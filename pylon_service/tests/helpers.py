import asyncio
import socket
import threading
import time
from collections.abc import Callable, Iterable
from typing import Any

import uvicorn


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("localhost", 0))
        return int(sock.getsockname()[1])


async def wait_for_background_tasks(tasks_to_wait: Iterable[asyncio.Task], timeout: float = 2.0) -> None:
    """
    Wait for background tasks to complete.

    Args:
        tasks_to_wait: Iterable of tasks to wait for.
        timeout: Maximum time to wait in seconds

    Raises:
        TimeoutError: If tasks don't complete within the timeout period
    """
    if not tasks_to_wait:
        return

    # Wait for all filtered tasks to complete
    done, pending = await asyncio.wait(tasks_to_wait, timeout=timeout)

    if pending:
        pending_names = [task.get_name() for task in pending]
        raise TimeoutError(f"Background tasks did not complete within {timeout}s: {pending_names}")


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
