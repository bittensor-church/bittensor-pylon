import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any, ParamSpec

from .queue import AbstractQueue, Task

logger = logging.getLogger(__name__)

P = ParamSpec("P")

TaskDefinition = Callable[P, Coroutine[Any, Any, None]]


class TaskProcessor:
    """
    A general-purpose background task processor that runs tasks (coroutines) asynchronously.
    It uses a queue as a backbone to store tasks and process them asynchronously.
    - Task registration is decoupled from execution so that this processor can work with
    any kind of centralized queue implementation.
    - Workers are essentially coroutines that are scheduled in the event loop to process tasks.
    They continuously monitor and pull tasks from the queue and execute them.
    - The processor itself has no builtin retry mechanism, so it is up to the caller to handle retries.
    """

    def __init__(self, queue: AbstractQueue, workers: int = 2, timeout: float | None = None) -> None:
        """
        Initialize the task processor.

        Args:
            workers: Maximum number of workers to process the tasks. default is 2.
            queue: Queue implementation to use.
        """
        self._worker_count = workers
        self._workers: list[asyncio.Task[None]] = []
        self._registered_tasks: dict[str, tuple[float | None, TaskDefinition]] = {}

        self._queue: AbstractQueue = queue
        self._timeout = timeout

        self._stop_event = asyncio.Event()
        self._running = False

    def register(self, name: str, *, timeout: float | None = None) -> Callable[[TaskDefinition], TaskDefinition]:
        """
        Decorator to register a task function. The 'task' can be submitted by the 'name' later.
        Args:
            name: Name of the task. The work can be submitted using this name. If the name is already registered,
            registration will be overridden.
            timeout: Timeout in seconds for the task to complete. If not specified, timeout set during initialization
            will be used.
        """

        def decorator(func: TaskDefinition) -> TaskDefinition:
            if name in self._registered_tasks:
                logger.warning(f"Task already registered, overriding existing task. task_name: {name}")

            self._registered_tasks[name] = (timeout, func)
            return func

        return decorator

    async def start(self) -> None:
        """
        Start the task processor workers.

        Raises:
            RuntimeError: If the processor is already running.
        """
        if self._running:
            raise RuntimeError("Task processor is already running")

        logger.info("Task processor starting...")
        self._running = True
        self._stop_event.clear()

        for i in range(1, self._worker_count + 1):
            worker_task = asyncio.create_task(self._worker(worker_id=i), name=f"background-worker-{i}")
            self._workers.append(worker_task)

        task_names = ", ".join(self._registered_tasks.keys())
        logger.info(f"Task processor started. workers: {len(self._workers)}, tasks: {task_names}")

    async def stop(self, timeout: float = 10.0) -> None:
        """
        Stop the background task processor and wait for workers to finish.

        Args:
            timeout: Maximum time in seconds to wait for workers to finish gracefully.
        """
        if not self._running:
            return

        logger.info("Task processor stopping...")
        self._stop_event.set()

        try:
            await asyncio.wait_for(
                asyncio.gather(*self._workers, return_exceptions=True),
                timeout=timeout,
            )
        except TimeoutError:
            logger.warning(f"Workers did not finish within timeout, cancelling remaining workers. timeout: {timeout}")
            for worker in self._workers:
                if not worker.done():
                    worker.cancel()

            await asyncio.gather(*self._workers, return_exceptions=True)

        self._workers.clear()
        self._running = False
        logger.info("Task processor stopped.")

    async def submit(
        self,
        task_name: str,
        *,
        args: tuple[Any, ...] | None = None,
        kwargs: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> None:
        """
        Submit a registered task for background execution. If the task processor is set for
        stopping, the task will be ignored.

        Args:
            task_name: Name of the registered task to execute.
            args: Positional args to pass to the task.
            kwargs: Keyword args to pass to the task function.
            timeout: Timeout in seconds for the task to complete. If not specified, uses the default timeout
            set during task registration or initialization.

        Raises:
            RuntimeError: If the processor is not running.
            ValueError: If the task name is not registered.
        """
        if not self._running or self._stop_event.is_set():
            logger.warning("Cannot submit task, task processor is not running.")
            return

        if task_name not in self._registered_tasks:
            raise ValueError(f"Task is not registered. task_name: {task_name}")

        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}

        await self._queue.put(Task(name=task_name, args=args, kwargs=kwargs, timeout=timeout))

    async def _worker(self, worker_id: int) -> None:
        logger.info(f"Starting worker. id: {worker_id}")

        while not self._stop_event.is_set():
            task = await self._queue.get(timeout=1.0)
            if task is None:
                continue
            await self._execute(worker_id, task)

        while not (self._queue.empty()):
            task = await self._queue.get(timeout=-1)
            if task is None:
                break

            await self._execute(worker_id, task)

        logger.info(f"Worker stopped. id: {worker_id}")

    async def _execute(self, worker_id: int, task: Task) -> None:
        timeout, func = self._registered_tasks[task.name]
        coro = func(*task.args, **task.kwargs)

        # Pick the first non-None timeout value. current task -> registered task -> processor
        timeout = next((t for t in (task.timeout, timeout, self._timeout) if t is not None), None)
        if timeout is not None:
            coro = asyncio.wait_for(coro, timeout=timeout)

        try:
            await coro
        except TimeoutError:
            logger.warning(f"Worker timed out while executing task. worker_id: {worker_id}, task: {task.name}")
        except Exception as e:
            logger.exception(
                f"Worker failed with error while executing task. worker_id: {worker_id}, task: {task.name}, error: {e}"
            )
        finally:
            await self._queue.task_done()
