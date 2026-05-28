import asyncio
import socket
import threading
import time
from collections.abc import Callable
from typing import Any

import uvicorn
from sqlalchemy import inspect

from pylon_service.api._unstable.tasks import ApplyWeights
from pylon_service.db.database import Base


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("localhost", 0))
        return int(sock.getsockname()[1])


async def wait_for_apply_weights_tasks(timeout: float = 2.0) -> None:
    """
    Wait for apply weights tasks to complete.

    Args:
        tasks_to_wait: Iterable of tasks to wait for.
        timeout: Maximum time to wait in seconds

    Raises:
        TimeoutError: If tasks don't complete within the timeout period
    """
    tasks_to_wait = [task._running_task for task in ApplyWeights.tasks_running if task._running_task is not None]
    if not tasks_to_wait:
        return

    current_loop = asyncio.get_running_loop()

    def completion_future_for(task: asyncio.Task) -> asyncio.Future[None]:
        completion_future = current_loop.create_future()

        def mark_completed() -> None:
            if not completion_future.done():
                completion_future.set_result(None)

        if task.done():
            mark_completed()
            return completion_future

        def on_task_done(_task: asyncio.Task) -> None:
            current_loop.call_soon_threadsafe(mark_completed)

        task.add_done_callback(on_task_done)

        if task.done():
            mark_completed()

        return completion_future

    completion_futures = [completion_future_for(task) for task in tasks_to_wait]

    try:
        await asyncio.wait_for(
            asyncio.gather(*completion_futures),
            timeout=timeout,
        )
    except TimeoutError as exc:
        for future in completion_futures:
            future.cancel()
        pending_names = [task.get_name() for task in tasks_to_wait if not task.done()]
        raise TimeoutError(f"Background tasks did not complete within {timeout}s: {pending_names}") from exc


async def wait_until(func: Callable[[], Any], timeout: float = 2.0, sleep_interval: float = 0.1) -> None:
    async with asyncio.timeout(timeout):
        while not func():
            await asyncio.sleep(sleep_interval)


def sync_wait_until(func: Callable[[], Any], timeout: float = 2.0, sleep_interval: float = 0.1) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if func():
            return
        time.sleep(sleep_interval)
    raise TimeoutError(f"Condition not met within {timeout}s")


def db_row_model_dump(model: Base, *, exclude: set[str] | None = None):
    exclude = exclude or set()
    return {
        column.key: getattr(model, column.key) for column in inspect(type(model)).columns if column.key not in exclude
    }


class UvicornServer:
    def __init__(self, app, host: str = "localhost", port: int = 8000, startup_timeout: float = 5.0):
        self.config = uvicorn.Config(app, host=host, port=port, log_level="debug")
        self.server = uvicorn.Server(self.config)
        self.startup_timeout = startup_timeout
        self._thread: threading.Thread | None = None

    def start(self):
        self._thread = threading.Thread(target=self.server.run, daemon=True)
        self._thread.start()
        elapsed_seconds = 0.0
        while not self.server.started:
            time.sleep(0.1)
            elapsed_seconds += 0.1
            if elapsed_seconds >= self.startup_timeout:
                self.stop()
                raise RuntimeError("Timeout while waiting for uvicorn server to start.")

    def stop(self):
        self.server.should_exit = True
        if self._thread:
            self._thread.join(timeout=10)
