import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Task:
    name: str
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    timeout: float | None = None


class AbstractQueue(ABC):
    """
    Abstract interface for queue used by TaskProcessor.
    """

    @abstractmethod
    async def put(self, task: Task) -> None:
        """
        Add a task to the queue.

        Args:
            task: Task to add to the queue.
        """

    @abstractmethod
    async def get(self, timeout: float) -> Task | None:
        """
        Remove and return an item from the queue.

        Args:
            timeout: Maximum time to wait for an item in seconds. If negative, return immediately.
        Returns:
            Task if available within timeout, None otherwise.
        """

    @abstractmethod
    async def task_done(self) -> None:
        """
        Call to indicate that a task is complete.
        """

    @abstractmethod
    def empty(self) -> bool:
        """
        Return True if the queue is empty, False otherwise.

        Returns:
            True if the queue is empty, False otherwise.
        """


class AsyncioQueue(AbstractQueue):
    """
    In-memory queue implementation using asyncio.Queue.
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[Task] = asyncio.Queue()

    async def put(self, task: Task) -> None:
        self._queue.put_nowait(task)

    async def get(self, timeout: float) -> Task | None:
        if timeout < 0:
            try:
                return self._queue.get_nowait()
            except asyncio.QueueEmpty:
                return None

        try:
            return await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except TimeoutError:
            return None

    async def task_done(self) -> None:
        self._queue.task_done()

    def empty(self) -> bool:
        return self._queue.empty()
