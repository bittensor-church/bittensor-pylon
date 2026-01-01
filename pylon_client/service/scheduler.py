"""
This module creates and manages an AsyncIOScheduler from apscheduler as a singleton.

The scheduler is initialized only once when 'create_scheduler' is called with the Litestar app.
Subsequent calls to 'create_scheduler' return the same scheduler instance. Ideally, 'create_scheduler'
should be called only once in the application's lifetime. Duplicate calls will log a warning,
suggesting that there is something wrong with the application startup.
"""

import datetime as dt
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler, BaseScheduler
from litestar import Litestar

from pylon_client._internal.common.types import NetUid
from pylon_client.service.bittensor.recent import (
    AbstractContext,
    IdentitySubnetContext,
    RecentObjectUpdateTaskExecutor,
    SubnetContext,
    UpdateRecentNeurons,
)
from pylon_client.service.identities import identities
from pylon_client.service.settings import recent_objects_settings
from pylon_client.service.stores import StoreName

logger = logging.getLogger(__name__)


_SCHEDULER: AsyncIOScheduler | None = None


# this is a simple way to organize the job definition code. When we have more jobs, we can
# move it to a separate module and think or more sophisticated way to organize them.
def _add_recent_neurons_job(app: Litestar, scheduler: BaseScheduler):
    contexts: list[AbstractContext] = []
    netuids: set[NetUid] = set()

    # fetch for all identities for identity and open access.
    for identity in identities.values():
        contexts.append(IdentitySubnetContext(identity.netuid, identity.wallet))
        if identity.netuid not in netuids:
            contexts.append(SubnetContext(identity.netuid))
            netuids.add(identity.netuid)

    # fetch for extra subnets specified in settings for open access.
    for netuid in recent_objects_settings.netuids:
        if netuid not in netuids:
            contexts.append(SubnetContext(netuid))

    timeout = recent_objects_settings.update_interval_seconds
    updater = UpdateRecentNeurons(app.stores.get(StoreName.RECENT_OBJECTS), app.state.bittensor_client_pool)
    executor = RecentObjectUpdateTaskExecutor(updater, timeout=timeout, contexts=contexts)

    scheduler.add_job(
        executor.run,
        id="update_recent_neurons",
        trigger="interval",
        seconds=recent_objects_settings.update_interval_seconds,
        next_run_time=dt.datetime.now(tz=dt.UTC),  # update immediately
    )


def create_scheduler(app: Litestar) -> AsyncIOScheduler:
    global _SCHEDULER

    if _SCHEDULER is not None:
        logger.warning("Scheduler already initialized and it should be initialized only once. Skipping.")
        return _SCHEDULER

    logger.info("Initializing scheduler.")
    _SCHEDULER = AsyncIOScheduler()

    _add_recent_neurons_job(app, _SCHEDULER)

    return _SCHEDULER
