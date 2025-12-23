import datetime as dt
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from litestar import Litestar

from pylon_client.service.settings import recent_objects_settings
from pylon_client.service.stores import StoreName
from pylon_client.service.tasks import UpdateRecentNeurons, UpdateTaskExecutor

logger = logging.getLogger(__name__)


_SCHEDULER: AsyncIOScheduler | None = None


def create_scheduler(app: Litestar) -> AsyncIOScheduler:
    global _SCHEDULER
    if _SCHEDULER is not None:
        logger.warning("Scheduler already initialized. This function should only be called once.")
        return _SCHEDULER

    logger.info("Initializing scheduler.")

    _SCHEDULER = AsyncIOScheduler()

    # configure jobs
    updater = UpdateRecentNeurons(app.stores.get(StoreName.RECENT_OBJECTS), app.state.bittensor_client_pool)
    executor = UpdateTaskExecutor(updater, timeout=recent_objects_settings.update_interval_seconds)
    _SCHEDULER.add_job(
        executor.run,
        trigger="interval",
        seconds=recent_objects_settings.update_interval_seconds,
        next_run_time=dt.datetime.now(tz=dt.UTC),  # update immediately
    )

    return _SCHEDULER
