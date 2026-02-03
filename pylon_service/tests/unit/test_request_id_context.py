import asyncio
import logging

import pytest
from litestar.types import HTTPRequestEvent, Message

from pylon_service.logging import PylonLogFilter
from pylon_service.middleware.request_id import (
    RequestIdMiddleware,
    current_request_id,
    reset_request_id,
    set_request_id,
)
from tests.helpers import wait_until


async def _receive() -> HTTPRequestEvent:
    return {"type": "http.request", "body": b"", "more_body": False}


async def _send(_: Message) -> None:
    return None


@pytest.mark.asyncio
async def test_request_id_is_task_local():
    ids: dict[str, str | None] = {}
    allow_exit = asyncio.Event()

    async def call(name: str) -> None:
        async def app(scope, receive, send):
            ids[name] = current_request_id()
            await allow_exit.wait()
            assert current_request_id() == ids[name]

        middleware = RequestIdMiddleware(app)
        await middleware({"type": "http", "method": "GET", "path": "/"}, _receive, _send)  # type: ignore[reportArgumentType]; use minimal scope needed by the RequestIdMiddleware

    try:
        tasks = [asyncio.create_task(call("a"))]
        tasks.append(asyncio.create_task(call("b")))
        await wait_until(lambda: len(ids) == 2)

        assert ids["a"] is not None
        assert ids["b"] is not None
        assert ids["a"] != ids["b"]
    finally:
        allow_exit.set()

    async with asyncio.timeout(2.0):
        await asyncio.gather(*tasks)


def test_logging_filter_injects_request_id():
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    PylonLogFilter().filter(record)
    assert getattr(record, "pylon_request_id", None) == "-"

    token = set_request_id("p999-abc")
    try:
        record2 = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="hello",
            args=(),
            exc_info=None,
        )
        PylonLogFilter().filter(record2)
        assert getattr(record2, "pylon_request_id", None) == "p999-abc"
    finally:
        reset_request_id(token)
