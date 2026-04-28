"""
Client for the WS frame recorder hosted inside the mitmproxy container.

The mitmproxy addon stores recorded WebSocket frames in memory and exposes
them via a tiny HTTP server. This module wraps that server with a small
sync client used by pytest fixtures.
"""

from __future__ import annotations

import enum
import json
from typing import Any

import httpx
from pydantic import BaseModel, TypeAdapter


class WSDirection(enum.StrEnum):
    """
    Direction of a recorded WebSocket frame relative to the proxy.
    """

    CLIENT_TO_SERVER = "c2s"
    SERVER_TO_CLIENT = "s2c"


class WSFrame(BaseModel):
    """
    A single WebSocket frame recorded by the mitmproxy addon.
    """

    direction: WSDirection
    is_text: bool
    content: str
    timestamp: float

    @property
    def content_json(self) -> Any:
        return json.loads(self.content)


_FRAMES_ADAPTER = TypeAdapter(list[WSFrame])


class WSRecorderClient:
    def __init__(self, url: str) -> None:
        self._url = url

    @property
    def frames(self) -> list[WSFrame]:
        response = httpx.get(self._url, timeout=5.0)
        response.raise_for_status()
        return _FRAMES_ADAPTER.validate_python(response.json())

    def clear(self) -> None:
        response = httpx.delete(self._url, timeout=5.0)
        response.raise_for_status()
