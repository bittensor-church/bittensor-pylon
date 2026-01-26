import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from litestar import Litestar

from pylon_service.bittensor.pool import BittensorClientPool
from pylon_service.scheduler import create_scheduler
from pylon_service.settings import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def bittensor_client_pool(app: Litestar) -> AsyncGenerator[None]:
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
async def scheduler_lifespan(app: Litestar) -> AsyncGenerator[None]:
    """
    Lifespan for APScheduler's scheduler.
    """
    scheduler = create_scheduler(app)
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown()
