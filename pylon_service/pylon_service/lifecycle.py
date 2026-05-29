import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from litestar import Litestar

from pylon_service.bittensor.contact import ContactFactory
from pylon_service.bittensor.pool import BittensorContactPool
from pylon_service.db.database import run_migrations
from pylon_service.scheduler import create_scheduler
from pylon_service.settings import settings
from pylon_service.tasks import reschedule_weight_tasks

logger = logging.getLogger(__name__)

contact_factory = ContactFactory()


@asynccontextmanager
async def bittensor_contact_pool_lifespan(app: Litestar) -> AsyncGenerator[None]:
    """
    Lifespan for Litestar app that creates a BittensorContactPool so endpoints may reuse contact routers.
    """
    logger.debug("Initializing bittensor contact pool.")
    async with BittensorContactPool(
        contact_factory=contact_factory,
        uri=settings.bittensor_network,
        archive_uri=settings.bittensor_archive_network,
        archive_blocks_cutoff=settings.bittensor_archive_blocks_cutoff,
    ) as pool:
        app.state.bittensor_contact_pool = pool
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


async def initialize_database(app: Litestar) -> None:
    """
    Initialize database and run migrations on startup.
    """
    logger.info("Running database migrations.")
    run_migrations()


async def reschedule_weight_tasks_on_startup(app: Litestar) -> None:
    """
    Reschedule weight tasks on startup.
    """
    logger.info("Rescheduling weight tasks.")
    await reschedule_weight_tasks(app)
