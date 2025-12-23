import datetime as dt
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from litestar import Litestar

from pylon_client._internal.common.constants import BLOCK_PROCESSING_TIME
from pylon_client._internal.common.types import NetUid
from pylon_client.service.bittensor.pool import BittensorClientPool
from pylon_client.service.identities import identities
from pylon_client.service.settings import settings
from pylon_client.service.stores import StoreName
from pylon_client.service.tasks import UpdateRecentNeurons, UpdateTaskExecutor

logger = logging.getLogger(__name__)


def _all_recent_objects_netuids() -> list[NetUid]:
    identity_netuids = [identity.netuid for identity in identities.values()]

    combined = set(settings.recent_objects_netuids) | set(identity_netuids)
    return list(combined)


def _recent_objects_update_task_interval() -> float:
    # Let's divide the hard limit by 2 and take whichever is smaller from the result and soft limit.
    # Set the interval to 10 blocks behind the result of the above step.
    # It'll 1) give us 120 seconds to update the cache before the soft limit, and 2) add two update passes
    # before the hard limit is reached.
    max_limit = min(settings.recent_objects_hard_limit // 2, settings.recent_objects_soft_limit)
    min_limit = max(max_limit - 10, 1)  # can't go below 1
    return min_limit * BLOCK_PROCESSING_TIME


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
async def ap_scheduler(app: Litestar) -> AsyncGenerator[None, None]:
    """
    Lifespan for APScheduler's scheduler.
    """
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        UpdateTaskExecutor(
            UpdateRecentNeurons(app.stores.get(StoreName.RECENT_OBJECTS), app.state.bittensor_client_pool)
        ).execute,
        "interval",
        seconds=_recent_objects_update_task_interval(),
        next_run_time=dt.datetime.now(),  # run first time immediately
    )
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown()
