from __future__ import annotations

import asyncio
import logging

from litestar.exceptions import ClientException
from litestar.types import ASGIApp, Receive, Scope, Send
from pylon_commons.timeout import TIMEOUT_HEADER

from pylon_service.exceptions import GatewayTimeoutException
from pylon_service.settings import settings

logger = logging.getLogger(__name__)

_TIMEOUT_HEADER_KEY = TIMEOUT_HEADER.lower().encode()


class RequestTimeoutMiddleware:
    """
    ASGI middleware that enforces per-request timeouts.

    Reads the X-Pylon-Timeout header (if present) to determine how long the client is willing to wait.
    The effective timeout is capped at the server's max_request_timeout_seconds setting.
    When no header is present, the server's default_request_timeout_seconds is used.

    On timeout, a 504 Gateway Timeout is raised for Litestar to handle.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        effective_timeout = self._resolve_timeout(scope)
        logger.debug("Setting request timeout to %s seconds.", effective_timeout)
        try:
            await asyncio.wait_for(self.app(scope, receive, send), timeout=effective_timeout)
        except TimeoutError as e:
            raise GatewayTimeoutException(detail="Request timed out") from e

    def _resolve_timeout(self, scope: Scope) -> float:
        for name, value in scope.get("headers", []):
            if name == _TIMEOUT_HEADER_KEY:
                try:
                    client_timeout = float(value.decode())
                except (ValueError, UnicodeDecodeError) as e:
                    raise ClientException(
                        detail=f"Invalid {TIMEOUT_HEADER} header value: {value.decode(errors='replace')}"
                    ) from e
                if client_timeout <= 0:
                    raise ClientException(
                        detail=f"{TIMEOUT_HEADER} header value must be positive, got {client_timeout}"
                    )
                if client_timeout > settings.max_request_timeout_seconds:
                    logger.warning(
                        "Value of X-Pylon-Timeout header (%ss) exceeds maximum allowed timeout (%ss).",
                        client_timeout,
                        settings.max_request_timeout_seconds,
                    )
                    return settings.max_request_timeout_seconds
                return client_timeout
        return settings.default_request_timeout_seconds
