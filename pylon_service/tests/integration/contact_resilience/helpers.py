import asyncio
import time
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import httpx
from websockets.exceptions import ConnectionClosed

from pylon_service.metrics import bittensor_operation_duration

TRANSIENT_RETRY_EXCEPTIONS = (ConnectionClosed, OSError, RuntimeError)


def histogram_count(labels: Mapping[str, str]) -> int:
    label_map = dict(labels)
    for metric_family in bittensor_operation_duration.collect():
        for sample in metric_family.samples:
            if sample.name.endswith("_count") and sample.labels == label_map:
                return int(sample.value)
    return 0


def assert_histogram_delta(labels: Mapping[str, str], before: int, *, at_least: int = 1) -> None:
    after = histogram_count(labels)
    assert after - before >= at_least, (labels, before, after)


async def retry_until_result(
    op: Callable[[], Awaitable[Any]],
    *,
    timeout: float = 20.0,
    attempt_timeout: float = 5.0,
    interval: float = 0.5,
    retryable_exceptions: tuple[type[Exception], ...] = TRANSIENT_RETRY_EXCEPTIONS,
) -> Any:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        per_attempt_timeout = min(attempt_timeout, remaining)
        try:
            return await asyncio.wait_for(op(), timeout=per_attempt_timeout)
        except TimeoutError as exc:
            last_error = exc
            await asyncio.sleep(interval)
        except retryable_exceptions as exc:
            last_error = exc
            await asyncio.sleep(interval)
    raise AssertionError(f"Operation did not succeed before timeout: {last_error!r}") from last_error


async def retry_until_failure(
    op: Callable[[], Awaitable[Any]],
    *,
    expected: type[Exception] | tuple[type[Exception], ...] = TRANSIENT_RETRY_EXCEPTIONS,
    timeout: float = 15.0,
    attempt_timeout: float = 5.0,
    interval: float = 0.5,
) -> Exception:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        per_attempt_timeout = min(attempt_timeout, remaining)
        try:
            await asyncio.wait_for(op(), timeout=per_attempt_timeout)
        except TimeoutError:
            pass
        except expected as exc:
            return exc
        await asyncio.sleep(interval)
    raise AssertionError("Operation did not fail before timeout")


def reset_proxy(proxy_name: str, control_url: str) -> None:
    httpx.post(f"{control_url}/reset", timeout=5.0).raise_for_status()


def add_timeout_toxic(
    proxy_name: str,
    control_url: str,
    *,
    name: str,
    toxic_type: str,
    stream: str,
    timeout_ms: int,
) -> None:
    response = httpx.post(
        f"{control_url}/proxies/{proxy_name}/toxics",
        json={
            "name": name,
            "type": toxic_type,
            "stream": stream,
            "attributes": {"timeout": timeout_ms},
        },
        timeout=5.0,
    )
    response.raise_for_status()


def remove_toxic(proxy_name: str, control_url: str, name: str) -> None:
    response = httpx.delete(f"{control_url}/proxies/{proxy_name}/toxics/{name}", timeout=5.0)
    response.raise_for_status()
