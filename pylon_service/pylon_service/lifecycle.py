import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from litestar import Litestar

from pylon_service.bittensor.contact import ContactFactory
from pylon_service.bittensor.pool import BittensorContactPool
from pylon_service.db.database import run_migrations
from pylon_service.evm.contact import EvmContact
from pylon_service.evm.contact_router import EvmContactRouter
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
async def evm_contact_lifespan(app: Litestar) -> AsyncGenerator[None]:
    """
    Lifespan for the EVM contact router. Connects to the configured main and archive EVM RPC nodes.
    Recent blocks are served from the main node; older blocks fall back to the archive node.
    """
    router = EvmContactRouter(
        main_contact=EvmContact(settings.evm_rpc_url),
        archive_contact=EvmContact(settings.evm_archive_rpc_url),
        archive_blocks_cutoff=settings.evm_archive_blocks_cutoff,
    )
    logger.debug("Opening EVM contact router (main=%s, archive=%s)", settings.evm_rpc_url, settings.evm_archive_rpc_url)
    try:
        await router.open()
        app.state.evm_contact_router = router
        yield
    finally:
        await router.close()


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
