import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from litestar import Litestar
from litestar.stores.memory import MemoryStore

from pylon._internal.background import TaskScheduler
from pylon.service.bittensor.cache.manager import BittensorCacheManager
from pylon.service.bittensor.cache.settings import settings as cache_settings
from pylon.service.bittensor.pool import BittensorClientPool
from pylon.service.bittensor.tasks import processor
from pylon.service.settings import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def bittensor_client_pool(app: Litestar) -> AsyncGenerator[None, None]:
    """
    Lifespan for litestar app that creates an instance of BittensorClientPool so that endpoints may reuse
    client instances.
    """
    logger.debug("Initializing bittensor client pool.")
    async with BittensorClientPool(
        uri=settings.bittensor_network,
        archive_uri=settings.bittensor_archive_network,
        archive_blocks_cutoff=settings.bittensor_archive_blocks_cutoff,
    ) as pool:
        app.state.bittensor_client_pool = pool
        yield


@asynccontextmanager
async def background_tasks(app: Litestar) -> AsyncGenerator[None, None]:
    scheduler = TaskScheduler(
        processor,
        interval=cache_settings.recent_neurons_update_task_interval,
        task_name="update-recent-neurons",
        eager=True,
        kwargs={
            "netuids": cache_settings.all_recent_neurons_netuids,
            "pool": app.state.bittensor_client_pool,
            "cache_manager": app.state.cache_manager,
        },
    )
    try:
        await processor.start()
        await scheduler.start()
        yield
    finally:
        await scheduler.stop()
        await processor.stop()


@asynccontextmanager
async def bittensor_cache_manager(app: Litestar) -> AsyncGenerator[None, None]:
    """
    Lifespan for providing a cache manager for bittensor. We need to maintain it throughout
    the app lifetime because it uses in-memory store.
    """
    store = MemoryStore()
    cache_manager = BittensorCacheManager(store)
    app.state.cache_manager = cache_manager
    yield
