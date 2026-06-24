import asyncio
from unittest.mock import patch

import pytest
from litestar.types import HTTPRequestEvent, Message

from pylon_service.logging import (
    _get_current_coroutine_name,
    add_coro_name_to_structlog,
    add_otel_resource_to_structlog,
    add_request_id_to_structlog,
)
from pylon_service.middleware.request_id import (
    RequestIdMiddleware,
    current_request_id,
    reset_request_id,
    set_request_id,
)
from pylon_service.settings import otel_settings
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


def test_structlog_processor_injects_request_id():
    assert add_request_id_to_structlog(None, "info", {"event": "hello"}) == {
        "event": "hello",
        "pylon_request_id": "-",
    }

    token = set_request_id("p999-abc")
    try:
        assert add_request_id_to_structlog(None, "info", {"event": "hello"}) == {
            "event": "hello",
            "pylon_request_id": "p999-abc",
        }
    finally:
        reset_request_id(token)


@pytest.mark.asyncio
async def test_structlog_processor_injects_coro_name():
    asyncio.current_task().set_name("my-task")  # type: ignore[union-attr]; always inside a task here
    assert add_coro_name_to_structlog(None, "info", {"event": "hello"}) == {
        "event": "hello",
        "coro_name": "my-task",
    }


def test_get_current_coroutine_name_without_event_loop():
    assert _get_current_coroutine_name() == "no-event-loop"


def test_get_current_coroutine_name_returns_fallback_on_error():
    class _RaisingTask:
        def get_name(self):
            raise RuntimeError("boom")

    with patch("pylon_service.logging.asyncio.current_task", return_value=_RaisingTask()):
        assert _get_current_coroutine_name() == "unknown-task"


def test_structlog_processor_injects_otel_resource_attributes():
    assert add_otel_resource_to_structlog(None, "info", {"event": "hello"}) == {
        "service.namespace": "bittensor-pylon",
        "service.name": "pylon_service",
        "deployment.environment.name": otel_settings.deployment_environment,
        "service.instance.id": otel_settings.service_instance_id,
        "event": "hello",
    }


def test_otel_resource_attributes_override_event_fields():
    assert add_otel_resource_to_structlog(None, "info", {"service.name": "override"}) == {
        "service.namespace": "bittensor-pylon",
        "deployment.environment.name": otel_settings.deployment_environment,
        "service.instance.id": otel_settings.service_instance_id,
        "service.name": "pylon_service",
    }
