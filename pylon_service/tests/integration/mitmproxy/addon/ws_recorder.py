"""
Mitmproxy addon that records every WebSocket message and exposes them via HTTP.

The addon is loaded by the `mitmproxy/mitmproxy` Docker container in e2e tests.
It keeps a list of frames in memory and runs a tiny stdlib HTTP server on a
configurable port (default 8474) with two routes:

- GET /frames → JSON list of recorded frames
- DELETE /frames → clear the list

The Docker image does not ship httpx/aiohttp, so we use only the standard
library.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from mitmproxy import http

logger = logging.getLogger(__name__)

_FRAMES: list[dict[str, Any]] = []
_FRAMES_LOCK = threading.Lock()


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/frames":
            self.send_response(404)
            self.end_headers()
            return
        with _FRAMES_LOCK:
            body = json.dumps(_FRAMES).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_DELETE(self) -> None:
        if self.path != "/frames":
            self.send_response(404)
            self.end_headers()
            return
        with _FRAMES_LOCK:
            _FRAMES.clear()
        self.send_response(204)
        self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        pass


class WSRecorderAddon:
    def __init__(self) -> None:
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def running(self) -> None:
        port = int(os.environ.get("PYLON_WS_RECORDER_PORT", "8474"))
        self._server = ThreadingHTTPServer(("0.0.0.0", port), _Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        logger.info(f"WS recorder HTTP server listening on :{port}")

    def websocket_message(self, flow: http.HTTPFlow) -> None:
        assert flow.websocket is not None
        msg = flow.websocket.messages[-1]
        if msg.is_text:
            entry = {
                "direction": "c2s" if msg.from_client else "s2c",
                "is_text": True,
                "content": msg.content.decode("utf-8", errors="replace"),
                "timestamp": msg.timestamp,
            }
        else:
            entry = {
                "direction": "c2s" if msg.from_client else "s2c",
                "is_text": False,
                "content": base64.b64encode(msg.content).decode("ascii"),
                "timestamp": msg.timestamp,
            }
        with _FRAMES_LOCK:
            _FRAMES.append(entry)

    def done(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None


addons = [WSRecorderAddon()]
