"""
This module creates and manages an AsyncIOScheduler from apscheduler as a singleton.

The scheduler is initialized only once when 'create_scheduler' is called with the Litestar app.
Subsequent calls to 'create_scheduler' return the same scheduler instance. Ideally, 'create_scheduler'
should be called only once in the application's lifetime. Duplicate calls will log a warning,
suggesting that there is something wrong with the application startup.
"""

import datetime as dt
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from litestar import Litestar

from pylon_client.service.settings import recent_objects_settings
from pylon_client.service.stores import StoreName
from pylon_client.service.tasks import RecentObjectUpdateTaskExecutor, UpdateRecentNeurons

logger = logging.getLogger(__name__)


_SCHEDULER: AsyncIOScheduler | None = None


def create_scheduler(app: Litestar) -> AsyncIOScheduler:
    global _SCHEDULER

    if _SCHEDULER is not None:
        logger.warning("Scheduler already initialized and it should be initialized only once. Skipping.")
        return _SCHEDULER

    logger.info("Initializing scheduler.")
    _SCHEDULER = AsyncIOScheduler()

    # configure jobs
    # this part can be designed in a better way out once we have more jobs and clarity.
    updater = UpdateRecentNeurons(app.stores.get(StoreName.RECENT_OBJECTS), app.state.bittensor_client_pool)
    executor = RecentObjectUpdateTaskExecutor(updater, timeout=recent_objects_settings.update_interval_seconds)
    _SCHEDULER.add_job(
        executor.run,
        trigger="interval",
        seconds=recent_objects_settings.update_interval_seconds,
        next_run_time=dt.datetime.now(tz=dt.UTC),  # update immediately
    )

    return _SCHEDULER
