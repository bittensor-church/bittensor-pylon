import asyncio
import logging
from enum import StrEnum
from typing import ClassVar, Self

from pylon_client._internal.common.models import Block, CommitReveal
from pylon_client._internal.common.types import CommitmentDataBytes, Hotkey, NetUid, Weight
from pylon_client.service.bittensor.client import AbstractBittensorClient
from pylon_client.service.metrics import (
    Attr,
    MetricsContext,
    Param,
    apply_weights_attempt_duration,
    apply_weights_job_duration,
    track_operation,
)
from pylon_client.service.settings import settings
from pylon_client.service.utils import get_epoch_containing_block

logger = logging.getLogger(__name__)


class ApplyWeights:
    JOB_NAME: ClassVar[str] = "apply_weights"
    tasks_running = set()

    class JobStatus(StrEnum):
        RUNNING = "running"
        TEMPO_EXPIRED = "tempo_expired"
        COMPLETED = "completed"
        FAILED = "failed"

    def __init__(self, client: AbstractBittensorClient):
        self._client: AbstractBittensorClient = client
        self._hotkey = client.hotkey

    @classmethod
    async def schedule(cls, client: AbstractBittensorClient, weights: dict[Hotkey, Weight], netuid: NetUid) -> Self:
        apply_weights = cls(client)
        task = asyncio.create_task(apply_weights.run_job(weights, netuid), name=cls.JOB_NAME)
        cls.tasks_running.add(task)
        task.add_done_callback(apply_weights._log_done)
        return apply_weights

    @track_operation(
        duration_metric=apply_weights_job_duration,
        labels={
            "netuid": Param("netuid"),
            "hotkey": Attr("_hotkey"),
        },
        inject_context="job_metrics",
    )
    async def run_job(
        self,
        weights: dict[Hotkey, Weight],
        netuid: NetUid,
        job_metrics: MetricsContext | None = None,
    ) -> None:
        start_block = await self._client.get_latest_block()

        tempo = get_epoch_containing_block(start_block.number, netuid)
        initial_tempo = tempo

        assert job_metrics is not None, "track_operation injects MetricsContext"
        job_metrics.set_label("status", self.JobStatus.RUNNING)

        retry_count = settings.weights_retry_attempts
        next_sleep_seconds = settings.weights_retry_delay_seconds
        max_sleep_seconds = next_sleep_seconds * 10
        for retry_no in range(retry_count + 1):
            latest_block = await self._client.get_latest_block()
            if latest_block.number > initial_tempo.end:
                job_metrics.set_label("status", self.JobStatus.TEMPO_EXPIRED)
                logger.error(
                    f"Apply weights job task cancelled: tempo ended "
                    f"({latest_block.number} > {initial_tempo.end}, {start_block.number=})"
                )
                return
            logger.info(
                f"apply weights {retry_no}, {latest_block.number=}, "
                f"still got {initial_tempo.end - latest_block.number} blocks left to go."
            )
            try:
                apply_weights = self._apply_weights(weights, netuid, latest_block)
                await asyncio.wait_for(asyncio.shield(apply_weights), 120)
                job_metrics.set_label("status", self.JobStatus.COMPLETED)
                return
            except Exception as exc:
                logger.error(
                    "Error executing %s: %s (retry %s)",
                    self.JOB_NAME,
                    exc,
                    retry_no,
                    exc_info=True,
                )
                if retry_no == retry_count:
                    job_metrics.set_label("status", self.JobStatus.FAILED)
                    raise
                logger.info(f"Sleeping for {next_sleep_seconds} seconds before retrying...")
                await asyncio.sleep(next_sleep_seconds)
                next_sleep_seconds = min(next_sleep_seconds * 2, max_sleep_seconds)

    @track_operation(
        duration_metric=apply_weights_attempt_duration,
        labels={
            "netuid": Param("netuid"),
            "hotkey": Attr("_hotkey"),
        },
    )
    async def _apply_weights(self, weights: dict[Hotkey, Weight], netuid: NetUid, latest_block: Block) -> None:
        hyperparams = await self._client.get_hyperparams(netuid, latest_block)
        if hyperparams is None:
            raise RuntimeError("Failed to fetch hyperparameters")
        commit_reveal_enabled = hyperparams.commit_reveal_weights_enabled
        if commit_reveal_enabled and commit_reveal_enabled != CommitReveal.DISABLED:
            logger.info(f"Commit weights (reveal enabled: {commit_reveal_enabled})")
            await self._client.commit_weights(netuid, weights)
        else:
            logger.info("Set weights (reveal disabled)")
            await self._client.set_weights(netuid, weights)

    def _log_done(self, job: asyncio.Task[None]) -> None:
        logger.info(f"Task finished {job}")
        self.tasks_running.discard(job)
        try:
            job.result()
        except Exception as exc:  # noqa: BLE001
            logger.error("Exception in weights job: %s", exc, exc_info=True)


class SetCommitment:
    """
    Sets commitment on chain with retry logic.
    """

    def __init__(self, client: AbstractBittensorClient):
        self._client: AbstractBittensorClient = client

    async def execute(self, netuid: NetUid, data: CommitmentDataBytes) -> None:
        retry_count = settings.commitment_retry_attempts
        next_sleep_seconds = settings.commitment_retry_delay_seconds
        max_sleep_seconds = next_sleep_seconds * 10
        last_exception: Exception | None = None

        for retry_no in range(retry_count + 1):
            logger.info(f"set commitment attempt {retry_no}")
            try:
                await asyncio.wait_for(
                    asyncio.shield(self._client.set_commitment(netuid, data)),
                    timeout=120,
                )
                logger.info("Commitment set successfully")
                return
            except Exception as exc:
                last_exception = exc
                logger.error(
                    "Error setting commitment: %s (retry %s)",
                    exc,
                    retry_no,
                    exc_info=True,
                )
                if retry_no < retry_count:
                    logger.info(f"Sleeping for {next_sleep_seconds} seconds before retrying...")
                    await asyncio.sleep(next_sleep_seconds)
                    next_sleep_seconds = min(next_sleep_seconds * 2, max_sleep_seconds)

        logger.error(f"Failed to set commitment after {retry_count + 1} attempts: {last_exception}")
        raise RuntimeError(
            f"Failed to set commitment after {retry_count + 1} attempts: {last_exception}"
        ) from last_exception
