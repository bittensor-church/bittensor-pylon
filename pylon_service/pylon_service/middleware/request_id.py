from __future__ import annotations

import itertools
import os
from contextvars import ContextVar, Token

from litestar.types import ASGIApp, Receive, Scope, Send

_REQUEST_ID: ContextVar[str | None] = ContextVar("pylon_request_id", default=None)
_REQUEST_COUNTER = itertools.count(1)
_PID = os.getpid()


def generate_request_id() -> str:
    return f"p{_PID}-{next(_REQUEST_COUNTER)}"


def current_request_id() -> str | None:
    return _REQUEST_ID.get()


def set_request_id(request_id: str) -> Token[str | None]:
    return _REQUEST_ID.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    _REQUEST_ID.reset(token)


class RequestIdMiddleware:
    """
    ASGI middleware that generates and sets a unique request ID for each incoming request.
    The request ID is stored in a context variable for access throughout the request lifecycle.

    An example use of the request ID is to include it in log messages for tracing.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        request_id = generate_request_id()
        token = set_request_id(request_id)
        try:
            await self.app(scope, receive, send)
        finally:
            reset_request_id(token)
