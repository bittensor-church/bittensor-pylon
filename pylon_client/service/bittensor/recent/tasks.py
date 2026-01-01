import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from litestar.stores.base import Store
from tenacity import AsyncRetrying, stop_after_delay

from pylon_client._internal.common.models import BittensorModel, SubnetNeurons
from pylon_client._internal.common.types import Timestamp
from pylon_client.service.bittensor.client import AbstractBittensorClient
from pylon_client.service.bittensor.pool import BittensorClientPool

from .adapter import RecentCacheAdapter
from .context import AbstractContext, SubnetContext

logger = logging.getLogger(__name__)

ModelT = TypeVar("ModelT", bound=BittensorModel)
ContextT = TypeVar("ContextT", bound=AbstractContext)


class UpdateRecentObject(ABC, Generic[ModelT, ContextT]):
    """
    An abstract task for implementing tasks for updating recent objects.
    """

    def __init__(self, store: Store, pool: BittensorClientPool) -> None:
        self._store = store
        self._pool = pool

    @property
    @abstractmethod
    def _model(self) -> type[ModelT]:
        pass

    @abstractmethod
    async def _get_object(self, context: ContextT, client: AbstractBittensorClient) -> tuple[Timestamp, ModelT]:
        pass

    async def execute(self, context: ContextT) -> None:
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
        timeout: int,
        retrying: AsyncRetrying | None = None,
    ) -> None:
        if retrying is None:
            lead_time = 10  # seconds before timeout.
            retry_time = max(timeout - lead_time, 0)
            retrying = AsyncRetrying(stop=stop_after_delay(retry_time), reraise=True)

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
                f"Timeout while waiting for UpdateRecentObject tasks to complete. "
                f"task={self._updater.__class__.__name__}"
            )
            return

        for context, result in zip(self._contexts, results):
            if isinstance(result, BaseException):
                logger.exception(
                    f"Failed to update recent object. task={self._updater.__class__.__name__},"
                    f" context: {context}, error: {result}"
                )

    async def task(self, context: AbstractContext) -> None:
        await self._retrying.wraps(self._updater.execute)(context)
