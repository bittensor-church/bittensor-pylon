import asyncio
import logging
from contextlib import suppress
from typing import Any

from .processor import TaskProcessor

logger = logging.getLogger(__name__)


class TaskScheduler:
    """
    Simple periodic task scheduler that submits tasks to the provided scheduler at regular intervals.
    """

    def __init__(
        self,
        processor: TaskProcessor,
        *,
        interval: float,
        task_name: str,
        args: tuple[Any, ...] | None = None,
        kwargs: dict[str, Any] | None = None,
        eager: bool = False,
    ) -> None:
        """
        Initialize the task scheduler.

        Args:
            processor: TaskProcessor to submit the task to.
            task_name: Name of the task to schedule.
            interval: Time interval in seconds between task submissions.
            args: Positional arguments to pass to the task.
            kwargs: Keyword arguments to pass to the task.
            eager: If True, submit the task immediately on startup, default is False.
        """
        self._processor = processor
        self._task_name = task_name
        self._interval = interval
        self._args = args
        self._kwargs = kwargs
        self._eager = eager

        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """
        Start the scheduler.

        This starts a background task that periodically submits the task to the queue.

        Raises:
            RuntimeError: If the scheduler is already running.
        """
        if self._task is not None:
            raise RuntimeError("Task scheduler is already running")

        logger.info(f"Starting scheduler for task. task_name: '{self._task_name}', interval: {self._interval}")

        self._task = asyncio.create_task(self._scheduler_loop(), name=f"scheduler-{self._task_name}")

    async def stop(self) -> None:
        """
        Stop the scheduler.

        This cancels the background task and waits for it to finish.
        """
        if self._task is None:
            return

        logger.info(f"Stopping scheduler for task. task_name: '{self._task_name}'")

        self._task.cancel()

        with suppress(asyncio.CancelledError):
            await self._task

        self._task = None
        logger.info(f"Scheduler stopped for task. task_name: '{self._task_name}'")

    async def _scheduler_loop(self) -> None:
        """
        Internal loop that periodically submits the task to the queue.
        """
        if self._eager:
            await self._processor.submit(self._task_name, args=self._args, kwargs=self._kwargs)
        while True:
            await asyncio.sleep(self._interval)
            await self._processor.submit(self._task_name, args=self._args, kwargs=self._kwargs)
