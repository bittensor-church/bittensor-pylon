import asyncio
from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, ClassVar, TypeVar

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.trace import Link, SpanContext
from opentelemetry.util.types import AttributeValue
import structlog
from prometheus_client import Histogram
from pylon_commons.models import Block, CommitReveal
from pylon_commons.types import (
    BlockNumber,
    CommitmentDataBytes,
    Hotkey,
    MechanismId,
    NetUid,
    NeuronUid,
    RevealedCommitmentData,
    Weight,
)
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from pylon_service.api.epoch import Epoch, get_epoch_containing_block, get_tempo_from_hyperparams
from pylon_service.api.services import HyperparamsNotFoundError
from pylon_service.bittensor.contact import BittensorPort
from pylon_service.db.models import TaskStatus, WeightTask
from pylon_service.db.weight_task import (
    create_weight_task_and_cancel_duplicate_tasks,
    get_weight_task_status,
    set_weight_task_start_block_number,
    update_weight_task_status,
)
from pylon_service.identities import Identity
from pylon_service.metrics import (
    Attr,
    LabelSource,
    apply_weights_attempt_duration,
    apply_weights_job_duration,
    set_commitment_job_duration,
    set_revealed_commitment_job_duration,
    track_operation,
)
from pylon_service.settings import settings
from pylon_service.tracing import TraceLinkType, get_current_valid_span_context

logger = structlog.stdlib.get_logger(__name__)
_tracer = trace.get_tracer(__name__)


class StopRetrying(Exception):
    pass


ReturnT = TypeVar("ReturnT")


class BackgroundTask[ReturnT](ABC):
    """
    Base class for background tasks with scheduling, tracking, retry loop, and done-callback lifecycle.
    """

    JOB_NAME: ClassVar[str]
    tasks_running: ClassVar[set["BackgroundTask[Any]"]]

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

    def __init__(self) -> None:
        self._running_task: asyncio.Task[ReturnT] | None = None
        self._request_span_context: SpanContext | None = None
        self._previous_attempt_context: SpanContext | None = None

    async def schedule(self) -> asyncio.Task[ReturnT]:
        await self._on_task_scheduled()

        self._request_span_context = get_current_valid_span_context()

        self._running_task = asyncio.create_task(self(), name=self.JOB_NAME)
        type(self).tasks_running.add(self)
        self._running_task.add_done_callback(self._on_task_done)
        return self._running_task

    async def __call__(self) -> ReturnT:
        return await self._submit_with_retries()

    @contextmanager
    def _attempt_span(self, attempt_number: int) -> Iterator[None]:
        links: list[Link] = []
        if self._request_span_context is not None:
            links.append(
                Link(
                    self._request_span_context,
                    attributes={TraceLinkType.ATTRIBUTE_KEY: TraceLinkType.ORIGINATING_REQUEST},
                )
            )
        if self._previous_attempt_context is not None:
            links.append(
                Link(
                    self._previous_attempt_context,
                    attributes={TraceLinkType.ATTRIBUTE_KEY: TraceLinkType.PREVIOUS_ATTEMPT},
                )
            )
        with _tracer.start_as_current_span(
            f"{self.JOB_NAME}.attempt",
            context=Context(),
            links=links,
            attributes={
                "attempt_number": attempt_number,
                **self._attempt_span_attributes(),
            },
        ):
            self._previous_attempt_context = get_current_valid_span_context()
            yield

    async def _submit_with_retries(self) -> ReturnT:
        prepared = False
        self._previous_attempt_context = None

        async def attempt() -> ReturnT:
            nonlocal prepared
            with self._attempt_span(retrying.statistics["attempt_number"]):
                if not prepared:
                    await self._prepare()
                    prepared = True
                return await self._single_attempt()

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
        try:
            return await retrying(attempt)
        except StopRetrying:
            raise
        except asyncio.CancelledError:
            # cancelled by asyncio during server shutdown
            raise
        except Exception:
            await self._on_task_failed()
            raise

    @staticmethod
    def _log_retry(retry_state: RetryCallState) -> None:
        if retry_state.outcome is None:
            raise RuntimeError("_log_retry called before an attempt")
        if retry_state.next_action is None:
            raise RuntimeError("_log_retry called when not retrying")
        exc = retry_state.outcome.exception()
        logger.error(
            "retryable_error",
            attempt=retry_state.attempt_number,
            error_type=type(exc).__name__,
            exc_info=True,
        )
        logger.info("retrying", sleep_seconds=retry_state.next_action.sleep)

    def _on_task_done(self, task: asyncio.Task[ReturnT]) -> None:
        type(self).tasks_running.discard(self)
        try:
            task.result()
        # This is a callback of a background task, so we ignore the result.
        except StopRetrying:
            pass
        except Exception as exc:  # noqa: BLE001
            logger.exception("task_failed", job_name=type(self).JOB_NAME, error_type=type(exc).__name__)
        else:
            logger.info("task_finished", task=task, job_name=self.JOB_NAME)

    def _attempt_span_attributes(self) -> dict[str, AttributeValue]:
        """
        Per-task attributes attached to each attempt span; overridden by subclasses that have them.
        """
        return {}

    async def _on_task_scheduled(self) -> None:
        pass

    async def _prepare(self) -> None:
        pass

    async def _on_task_failed(self) -> None:
        pass

    @property
    @abstractmethod
    def _retry_attempts(self) -> int: ...

    @property
    @abstractmethod
    def _retry_delay_seconds(self) -> int: ...

    @abstractmethod
    async def _single_attempt(self) -> ReturnT: ...


class ApplyWeights(
    BackgroundTask[None],
    duration_metric=apply_weights_job_duration,
    metric_labels={"netuid": Attr("_netuid"), "hotkey": Attr("_hotkey")},
):
    JOB_NAME: ClassVar[str] = "apply_weights"

    def __init__(
        self,
        identity: Identity,
        client: BittensorPort,
        weights: dict[Hotkey, Weight],
        netuid: NetUid,
        mechanism_id: MechanismId,
    ):
        super().__init__()
        self._client = client
        self._hotkey = client.hotkey
        self._weights = weights
        self._netuid = netuid
        self._mechanism_id = mechanism_id
        self._identity = identity
        self._is_rescheduled: bool = False
        self._initial_tempo: Epoch | None = None
        self._start_block_number: BlockNumber | None = None
        self._task_id: int | None = None

    @classmethod
    def from_persisted_task(cls, identity: Identity, client: BittensorPort, weight_task: WeightTask) -> "ApplyWeights":
        task = cls(identity, client, weight_task.weights, weight_task.netuid, weight_task.mechanism_id)
        task._is_rescheduled = True
        task._start_block_number = weight_task.start_block_number
        task._task_id = weight_task.id
        return task

    @property
    def _retry_attempts(self) -> int:
        return settings.weights_retry_attempts

    @property
    def _retry_delay_seconds(self) -> int:
        return settings.weights_retry_delay_seconds

    def _attempt_span_attributes(self) -> dict[str, AttributeValue]:
        """
        Attach netuid and hotkey to each attempt span for trace filtering.
        """
        return {"netuid": self._netuid, "hotkey": self._hotkey}

    async def _on_task_scheduled(self) -> None:
        if self._is_rescheduled:
            return

        self._task_id = await create_weight_task_and_cancel_duplicate_tasks(
            identity_name=self._identity.identity_name,
            weights=self._weights,
            netuid=self._netuid,
            mechanism_id=self._mechanism_id,
            hotkey=self._hotkey,
        )

    async def _prepare(self) -> None:
        if self._task_id is None:
            raise RuntimeError("Task not persisted before _prepare")
        if self._start_block_number is not None:
            start_block = await self._client.get_block(self._start_block_number)
            if start_block is None:
                raise RuntimeError("Failed to get block %s", self._start_block_number)
        else:
            start_block = await self._client.get_latest_block()
            await set_weight_task_start_block_number(self._task_id, start_block.number)
            self._start_block_number = start_block.number

        hyperparams = await self._client.get_hyperparams(self._netuid, start_block)
        tempo = get_tempo_from_hyperparams(hyperparams)
        self._initial_tempo = get_epoch_containing_block(self._start_block_number, self._netuid, tempo)

    async def _single_attempt(self) -> None:
        if self._initial_tempo is None:
            raise RuntimeError("_initial_tempo not set before an attempt")
        if self._task_id is None:
            raise RuntimeError("Task not persisted before an attempt")
        task_status = await get_weight_task_status(self._task_id)
        if task_status != TaskStatus.RUNNING:
            logger.warning(
                "weight_task_stopped",
                identity_name=self._identity.identity_name,
                mechanism_id=self._mechanism_id,
                status=task_status,
            )
            raise StopRetrying("Task stopped")
        latest_block = await self._client.get_latest_block()
        if latest_block.number > self._initial_tempo.end:
            await update_weight_task_status(self._task_id, TaskStatus.EXPIRED)
            logger.error(
                "weight_task_expired",
                identity_name=self._identity.identity_name,
                mechanism_id=self._mechanism_id,
                block_number=latest_block.number,
                tempo_end=self._initial_tempo.end,
            )
            raise StopRetrying("Task expired")

        remaining = self._initial_tempo.end - latest_block.number
        logger.info(
            "apply_weights_attempt",
            block_number=latest_block.number,
            remaining=remaining,
        )
        await asyncio.wait_for(asyncio.shield(self._apply_weights(latest_block)), 120)
        # do not set status to SUCCEEDED if the task was cancelled while running
        await update_weight_task_status(self._task_id, TaskStatus.SUCCEEDED, only_if_running=True)

    async def _on_task_failed(self) -> None:
        try:
            if self._task_id is not None:
                # do not set status to FAILED if the task was cancelled while running
                await update_weight_task_status(self._task_id, TaskStatus.FAILED, only_if_running=True)
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "weight_task_status_update_failed",
                identity_name=self._identity.identity_name,
                mechanism_id=self._mechanism_id,
                error_type=type(exc).__name__,
            )

    async def _translate_weights(self, latest_block: Block) -> dict[NeuronUid, Weight]:
        translated_weights: dict[NeuronUid, Weight] = {}
        missing: list[Hotkey] = []
        neurons = await self._client.get_neurons_list(self._netuid, latest_block)
        hotkey_to_uid = {neuron.hotkey: neuron.uid for neuron in neurons}
        for hotkey, weight in self._weights.items():
            uid = hotkey_to_uid.get(hotkey)
            if uid is None:
                missing.append(hotkey)
                continue
            translated_weights[uid] = weight
        if missing:
            logger.warning(
                "weight_hotkeys_missing",
                missing=missing,
            )
        return translated_weights

    @track_operation(
        duration_metric=apply_weights_attempt_duration,
        labels={
            "netuid": Attr("_netuid"),
            "hotkey": Attr("_hotkey"),
        },
    )
    async def _apply_weights(self, latest_block: Block) -> None:
        logger.info("applying_weights")
        hyperparams = await self._client.get_hyperparams(self._netuid, latest_block)
        if hyperparams is None:
            raise HyperparamsNotFoundError("Failed to fetch hyperparameters")

        translated_weights = await self._translate_weights(latest_block)
        commit_reveal_enabled = hyperparams.commit_reveal_weights_enabled
        if commit_reveal_enabled and commit_reveal_enabled != CommitReveal.DISABLED:
            await self._client.commit_weights(self._netuid, self._mechanism_id, translated_weights)
        else:
            await self._client.set_weights(self._netuid, self._mechanism_id, translated_weights)


class SetCommitment(
    BackgroundTask[None],
    duration_metric=set_commitment_job_duration,
    metric_labels={"netuid": Attr("_netuid")},
):
    """
    Sets commitment on chain with retry logic.
    """

    JOB_NAME: ClassVar[str] = "set_commitment"

    def __init__(
        self,
        client: BittensorPort,
        netuid: NetUid,
        data: CommitmentDataBytes,
    ):
        super().__init__()
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
        logger.info("set_commitment_attempt")
        await asyncio.wait_for(
            asyncio.shield(self._client.set_commitment(self._netuid, self._data)),
            timeout=120,
        )


class SetRevealedCommitment(
    BackgroundTask[int],
    duration_metric=set_revealed_commitment_job_duration,
    metric_labels={"netuid": Attr("_netuid")},
):
    """
    Sets revealed commitment on chain with retry logic.

    Returns:
            Reveal round for revealed commitment created.
    """

    JOB_NAME: ClassVar[str] = "set_revealed_commitment"

    def __init__(
        self,
        client: BittensorPort,
        netuid: NetUid,
        commitment: RevealedCommitmentData,
        blocks_until_reveal: int,
    ):
        super().__init__()
        self._client = client
        self._netuid = netuid
        self._commitment = commitment
        self._blocks_until_reveal = blocks_until_reveal

    @property
    def _retry_attempts(self) -> int:
        return settings.commitment_retry_attempts

    @property
    def _retry_delay_seconds(self) -> int:
        return settings.commitment_retry_delay_seconds

    async def _single_attempt(self) -> int:
        logger.info("set_revealed_commitment_attempt")
        return await asyncio.wait_for(
            asyncio.shield(
                self._client.set_revealed_commitment(self._netuid, self._commitment, self._blocks_until_reveal)
            ),
            timeout=120,
        )
