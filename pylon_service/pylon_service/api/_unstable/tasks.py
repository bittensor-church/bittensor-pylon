import asyncio
import logging
from abc import ABC, abstractmethod
from typing import ClassVar

from prometheus_client import Histogram
from pylon_commons.models import Block, CommitReveal
from pylon_commons.types import CommitmentDataBytes, Hotkey, NetUid, Weight
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from pylon_service.api._unstable.utils import Epoch, get_epoch_containing_block
from pylon_service.bittensor.client import AbstractBittensorClient
from pylon_service.metrics import (
    Attr,
    LabelSource,
    apply_weights_attempt_duration,
    apply_weights_job_duration,
    set_commitment_job_duration,
    track_operation,
)
from pylon_service.settings import settings

logger = logging.getLogger(__name__)


class StopRetrying(Exception):
    pass


class BackgroundTask(ABC):
    """
    Base class for background tasks with scheduling, tracking, retry loop, and done-callback lifecycle.
    """

    JOB_NAME: ClassVar[str]
    tasks_running: ClassVar[set[asyncio.Task]]

    def __init_subclass__(
        cls,
        duration_metric: Histogram,
        metric_labels: dict[str, LabelSource],
        **kwargs: object,
    ) -> None:
        super().__init_subclass__(**kwargs)
        cls.tasks_running = set()
        cls.__call__ = track_operation(
            duration_metric,
            operation_name="run_job",
            labels=metric_labels,
        )(cls.__call__)

    def schedule(self) -> asyncio.Task:
        task = asyncio.create_task(self(), name=self.JOB_NAME)
        type(self).tasks_running.add(task)
        task.add_done_callback(self._on_task_done)
        return task

    async def __call__(self) -> None:
        await self._submit_with_retries()

    async def _submit_with_retries(self) -> None:
        prepared = False

        async def attempt() -> None:
            nonlocal prepared
            if not prepared:
                await self._prepare()
                prepared = True
            await self._single_attempt()

        retrying = AsyncRetrying(
            stop=stop_after_attempt(self._retry_attempts + 1),
            wait=wait_exponential(
                min=self._retry_delay_seconds,
                max=self._retry_delay_seconds * 10,
            ),
            retry=retry_if_exception(lambda e: not isinstance(e, StopRetrying) and isinstance(e, Exception)),
            before_sleep=self._log_retry,
            reraise=True,
        )
        await retrying(attempt)

    @staticmethod
    def _log_retry(retry_state: RetryCallState) -> None:
        assert retry_state.outcome is not None, "before_sleep is only called after an attempt"
        assert retry_state.next_action is not None, "before_sleep is only called when retrying"
        exc = retry_state.outcome.exception()
        logger.error(
            "Retryable error (attempt %s): %s: %s",
            retry_state.attempt_number,
            type(exc).__name__,
            exc,
            exc_info=True,
        )
        logger.info("Retrying in %.1f seconds...", retry_state.next_action.sleep)

    def _on_task_done(self, task: asyncio.Task[None]) -> None:
        type(self).tasks_running.discard(task)
        try:
            task.result()
        # This is a callback of a background task so we ignore the result.
        except Exception as exc:  # noqa: BLE001
            logger.exception("Task %s failed with an exception: %s: %s", type(self).JOB_NAME, type(exc).__name__, exc)
        else:
            logger.info("Task %s (%s) finished successfully.", task, self.JOB_NAME)

    async def _prepare(self) -> None:
        pass

    @property
    @abstractmethod
    def _retry_attempts(self) -> int: ...

    @property
    @abstractmethod
    def _retry_delay_seconds(self) -> int: ...

    @abstractmethod
    async def _single_attempt(self) -> None: ...


class ApplyWeights(
    BackgroundTask,
    duration_metric=apply_weights_job_duration,
    metric_labels={"netuid": Attr("_netuid"), "hotkey": Attr("_hotkey")},
):
    JOB_NAME: ClassVar[str] = "apply_weights"

    def __init__(
        self,
        client: AbstractBittensorClient,
        weights: dict[Hotkey, Weight],
        netuid: NetUid,
    ):
        self._client = client
        self._weights = weights
        self._netuid = netuid
        self._hotkey = client.hotkey
        self._start_block: Block | None = None
        self._initial_tempo: Epoch | None = None

    @property
    def _retry_attempts(self) -> int:
        return settings.weights_retry_attempts

    @property
    def _retry_delay_seconds(self) -> int:
        return settings.weights_retry_delay_seconds

    async def _prepare(self) -> None:
        self._start_block = await self._client.get_latest_block()
        self._initial_tempo = get_epoch_containing_block(self._start_block.number, self._netuid)

    async def _single_attempt(self) -> None:
        assert self._initial_tempo is not None, "_prepare sets _initial_tempo before retries"
        latest_block = await self._client.get_latest_block()
        if latest_block.number > self._initial_tempo.end:
            raise StopRetrying(f"Tempo ended: {latest_block.number} > {self._initial_tempo.end}")

        remaining = self._initial_tempo.end - latest_block.number
        logger.info(
            "apply weights attempt, latest_block=%s, still got %s blocks left to go.",
            latest_block.number,
            remaining,
        )

        await asyncio.wait_for(asyncio.shield(self._apply_weights(latest_block)), 120)

    @track_operation(
        duration_metric=apply_weights_attempt_duration,
        labels={
            "netuid": Attr("_netuid"),
            "hotkey": Attr("_hotkey"),
        },
    )
    async def _apply_weights(self, latest_block: Block) -> None:
        hyperparams = await self._client.get_hyperparams(self._netuid, latest_block)
        if hyperparams is None:
            raise RuntimeError("Failed to fetch hyperparameters")
        commit_reveal_enabled = hyperparams.commit_reveal_weights_enabled
        if commit_reveal_enabled and commit_reveal_enabled != CommitReveal.DISABLED:
            logger.info(f"Commit weights (reveal enabled: {commit_reveal_enabled})")
            await self._client.commit_weights(self._netuid, self._weights)
        else:
            logger.info("Set weights (reveal disabled)")
            await self._client.set_weights(self._netuid, self._weights)


class SetCommitment(
    BackgroundTask,
    duration_metric=set_commitment_job_duration,
    metric_labels={"netuid": Attr("_netuid")},
):
    """
    Sets commitment on chain with retry logic.
    """

    JOB_NAME: ClassVar[str] = "set_commitment"

    def __init__(
        self,
        client: AbstractBittensorClient,
        netuid: NetUid,
        data: CommitmentDataBytes,
    ):
        self._client = client
        self._netuid = netuid
        self._data = data

    @property
    def _retry_attempts(self) -> int:
        return settings.commitment_retry_attempts

    @property
    def _retry_delay_seconds(self) -> int:
        return settings.commitment_retry_delay_seconds

    async def _single_attempt(self) -> None:
        logger.info("Set commitment attempt")
        await asyncio.wait_for(
            asyncio.shield(self._client.set_commitment(self._netuid, self._data)),
            timeout=120,
        )
