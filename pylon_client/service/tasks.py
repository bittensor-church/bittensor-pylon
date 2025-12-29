import asyncio
import logging
from abc import ABC, abstractmethod
from enum import StrEnum
from typing import ClassVar, Generic, Self, TypeVar

from litestar.stores.base import Store
from tenacity import AsyncRetrying, stop_after_delay

from pylon_client._internal.common.models import BittensorModel, Block, CommitReveal, SubnetNeurons
from pylon_client._internal.common.types import CommitmentDataBytes, Hotkey, NetUid, Timestamp, Weight
from pylon_client.service.bittensor.client import AbstractBittensorClient
from pylon_client.service.bittensor.pool import BittensorClientPool
from pylon_client.service.bittensor.recent import (
    AbstractContext,
    IdentitySubnetContext,
    RecentCacheAdapter,
    SubnetContext,
)
from pylon_client.service.identities import identities
from pylon_client.service.metrics import (
    Attr,
    MetricsContext,
    Param,
    apply_weights_attempt_duration,
    apply_weights_job_duration,
    track_operation,
)
from pylon_client.service.settings import recent_objects_settings, settings
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


TModel = TypeVar("TModel", bound=BittensorModel)
TContext = TypeVar("TContext", bound=AbstractContext)


class UpdateRecentObject(ABC, Generic[TModel, TContext]):
    """
    An abstract task for implementing tasks for updating recent objects.
    """

    def __init__(self, store: Store, pool: BittensorClientPool) -> None:
        self._store = store
        self._pool = pool

    @property
    @abstractmethod
    def _model(self) -> type[TModel]:
        pass

    @abstractmethod
    async def _get_object(self, context: TContext, client: AbstractBittensorClient) -> tuple[Timestamp, TModel]:
        pass

    @classmethod
    @abstractmethod
    def contexts(cls) -> list[TContext]:
        pass

    async def execute(self, context: TContext) -> None:
        async with self._pool.acquire(wallet=context.wallet) as client:
            try:
                timestamp, object_ = await self._get_object(context, client)
            except Exception as e:
                logger.exception(f"Failed to fetch recent object. object={self._model.__name__}, error: {e}")
                raise

        cache_key = context.build_key(self._model)
        cache_adapter = RecentCacheAdapter(cache_key, self._store, self._model)
        await cache_adapter.save(timestamp, object_)

        logger.info(f"Updated recent object. context: {context}, object: {self._model.__name__}")


class UpdateRecentNeurons(UpdateRecentObject[SubnetNeurons, SubnetContext]):
    """
    Handles the update process for recent neurons within a subnet context.
    """

    @property
    def _model(self) -> type[SubnetNeurons]:
        return SubnetNeurons

    async def _get_object(
        self,
        context: SubnetContext,
        client: AbstractBittensorClient,
    ) -> tuple[Timestamp, SubnetNeurons]:
        block = await client.get_latest_block()
        timestamp = await client.get_block_timestamp(block)
        neurons = await client.get_neurons(context.netuid, block)
        return timestamp, neurons

    @classmethod
    def contexts(cls) -> list[SubnetContext]:
        contexts: list[SubnetContext] = []
        netuids: set[NetUid] = set()

        # fetch for all identities for identity and open access.
        for identity in identities.values():
            contexts.append(IdentitySubnetContext(identity.netuid, identity.wallet))
            if identity.netuid not in netuids:
                contexts.append(SubnetContext(identity.netuid))
                netuids.add(identity.netuid)

        # fetch for extra subnets specified in settings for open access.
        for netuid in recent_objects_settings.netuids:
            if netuid not in netuids:
                contexts.append(SubnetContext(netuid))

        return contexts


class RecentObjectUpdateTaskExecutor:
    """
    An executor class for executing UpdateRecentObject tasks with configured contexts.
    This class implements batching and retrying strategies for updating recent objects.
    """

    # for now, the object for all contexts is updated in parallel. later we can implement more
    # sophisticated batching and retrying logic based on timeout.

    def __init__(self, updater: UpdateRecentObject, timeout: int) -> None:
        self._updater = updater
        self._timeout = timeout

    async def run(self) -> None:
        contexts = self._updater.contexts()
        tasks = [self.task(s) for s in contexts]
        try:
            async with asyncio.timeout(self._timeout):
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for context, result in zip(contexts, results):
                    if isinstance(result, BaseException):
                        logger.exception(
                            f"Failed to update recent object. task={self._updater.__class__.__name__},"
                            f" context: {context}, error: {result}"
                        )

        except TimeoutError:
            logger.exception(
                f"Timeout while waiting for UpdateRecentObject tasks to complete. "
                f"task={self._updater.__class__.__name__}"
            )

    async def task(self, context: AbstractContext) -> None:
        lead_time = 10  # seconds before timeout.
        retry_time = max(self._timeout - lead_time, 0)

        retrying = AsyncRetrying(stop=stop_after_delay(retry_time), reraise=True)

        await retrying.wraps(self._updater.execute)(context)
