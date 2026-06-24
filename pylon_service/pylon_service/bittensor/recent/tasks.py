import asyncio
from abc import ABC, abstractmethod

import structlog
from litestar.stores.base import Store
from pylon_commons.models import BittensorModel, SubnetNeurons
from tenacity import AsyncRetrying, stop_before_delay, wait_exponential

from pylon_service.bittensor.contact import BittensorPort
from pylon_service.bittensor.exceptions import SubnetStateUnavailable
from pylon_service.bittensor.pool import BittensorContactPool

from .adapter import RecentCacheAdapter
from .context import AbstractContext, SubnetContext

logger = structlog.stdlib.get_logger(__name__)


class _SkipRecentObjectUpdate(Exception):
    """Raised when a recent-object update should be skipped without retrying this run."""


class UpdateRecentObject[ModelT: BittensorModel, ContextT: AbstractContext](ABC):
    """
    An abstract task for implementing tasks for updating recent objects.
    """

    def __init__(self, store: Store, pool: BittensorContactPool) -> None:
        self._store = store
        self._pool = pool

    @property
    @abstractmethod
    def _model(self) -> type[ModelT]:
        pass

    @abstractmethod
    async def _get_object(self, context: ContextT, client: BittensorPort) -> ModelT:
        pass

    async def execute(self, context: ContextT) -> None:
        async with self._pool.acquire(wallet=context.wallet) as client:
            try:
                object_ = await self._get_object(context, client)
            except _SkipRecentObjectUpdate as exc:
                logger.warning(
                    "skipping_recent_object_update",
                    context=context,
                    object=self._model.__name__,
                    reason=str(exc),
                )
                return
            except Exception:
                logger.exception("recent_object_fetch_failed", object=self._model.__name__)
                raise

        cache_key = context.build_key(self._model)
        cache_adapter = RecentCacheAdapter(cache_key, self._store, self._model)
        await cache_adapter.save(object_)

        logger.info("recent_object_updated", context=context, object=self._model.__name__)


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
        client: BittensorPort,
    ) -> SubnetNeurons:
        block = await client.get_latest_block()
        try:
            return await client.get_neurons(context.netuid, block)
        except SubnetStateUnavailable as exc:
            raise _SkipRecentObjectUpdate(
                f"subnet state is unavailable for netuid {context.netuid} at block {block.number}; "
                "the subnet may not exist yet"
            ) from exc


class RecentObjectUpdateTaskExecutor:
    """
    An executor class for executing UpdateRecentObject tasks with configured contexts.
    This class implements batching and retrying strategies for updating recent objects.
    """

    # for now, the object for all contexts is updated in parallel. later we can implement more
    # sophisticated batching and retrying logic based on timeout.

    def __init__(
        self,
        updater: UpdateRecentObject,
        contexts: list[AbstractContext],
        timeout: float,
        retrying: AsyncRetrying | None = None,
    ) -> None:
        if retrying is None:
            lead_time = 10  # seconds before timeout.
            retry_time = max(timeout - lead_time, 0)
            retrying = AsyncRetrying(
                wait=wait_exponential(multiplier=10, min=10, max=120),
                stop=stop_before_delay(retry_time),
                reraise=True,
            )

        self._updater = updater
        self._contexts = contexts
        self._timeout = timeout
        self._retrying = retrying

    async def run(self) -> None:
        tasks = [self.task(s) for s in self._contexts]
        try:
            async with asyncio.timeout(self._timeout):
                results = await asyncio.gather(*tasks, return_exceptions=True)
        except TimeoutError:
            logger.exception(
                "update_recent_object_tasks_timeout",
                task=self._updater.__class__.__name__,
            )
            return

        for context, result in zip(self._contexts, results):
            if isinstance(result, BaseException):
                logger.exception(
                    "recent_object_update_failed",
                    task=self._updater.__class__.__name__,
                    context=context,
                    exc_info=result,
                )

    async def task(self, context: AbstractContext) -> None:
        await self._retrying.wraps(self._updater.execute)(context)
