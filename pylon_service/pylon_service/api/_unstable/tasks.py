import asyncio
import logging
from abc import ABC, abstractmethod
from typing import ClassVar, TypeVar

from prometheus_client import Histogram
from pylon_commons.models import Block, CommitReveal
from pylon_commons.types import (
    CommitmentDataBytes,
    Hotkey,
    MechanismId,
    NetUid,
    NeuronUid,
    RevealedCommitmentData,
    Tempo,
    Weight,
)
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from pylon_service.api._unstable.utils import Epoch, get_epoch_containing_block
from pylon_service.bittensor.contact import BittensorPort
from pylon_service.metrics import (
    Attr,
    LabelSource,
    apply_weights_attempt_duration,
    apply_weights_job_duration,
    set_commitment_job_duration,
    set_revealed_commitment_job_duration,
    track_operation,
)
from pylon_service.service_errors import HyperparamsNotFoundError
from pylon_service.settings import settings

logger = logging.getLogger(__name__)


class StopRetrying(Exception):
    pass


ReturnT = TypeVar("ReturnT")


class BackgroundTask[ReturnT](ABC):
    """
    Base class for background tasks with scheduling, tracking, retry loop, and done-callback lifecycle.
    """

    JOB_NAME: ClassVar[str]
    tasks_running: ClassVar[set[asyncio.Task[object]]]

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

    def schedule(self) -> asyncio.Task[ReturnT]:
        task = asyncio.create_task(self(), name=self.JOB_NAME)
        type(self).tasks_running.add(task)
        task.add_done_callback(self._on_task_done)
        return task

    async def __call__(self) -> ReturnT:
        return await self._submit_with_retries()

    async def _submit_with_retries(self) -> ReturnT:
        prepared = False

        async def attempt() -> ReturnT:
            nonlocal prepared
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
        return await retrying(attempt)

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

    def _on_task_done(self, task: asyncio.Task[ReturnT]) -> None:
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
    async def _single_attempt(self) -> ReturnT: ...


class ApplyWeights(
    BackgroundTask[None],
    duration_metric=apply_weights_job_duration,
    metric_labels={"netuid": Attr("_netuid"), "hotkey": Attr("_hotkey")},
):
    JOB_NAME: ClassVar[str] = "apply_weights"

    def __init__(
        self,
        client: BittensorPort,
        weights: dict[Hotkey, Weight],
        netuid: NetUid,
        mechanism_id: MechanismId,
    ):
        self._client = client
        self._weights = weights
        self._netuid = netuid
        self._mechanism_id = mechanism_id
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
        hyperparams = await self._client.get_hyperparams(self._netuid, self._start_block)
        tempo = hyperparams.tempo if hyperparams and hyperparams.tempo else Tempo(360)
        self._initial_tempo = get_epoch_containing_block(self._start_block.number, self._netuid, tempo)

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
                "Some of the hotkeys passed for weight commitment are missing. Weights will not be committed for: %s",
                missing,
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
        logger.info("Applying weights")
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
        logger.info("Set revealed commitment attempt")
        return await asyncio.wait_for(
            asyncio.shield(
                self._client.set_revealed_commitment(self._netuid, self._commitment, self._blocks_until_reveal)
            ),
            timeout=120,
        )
