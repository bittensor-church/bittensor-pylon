from __future__ import annotations

import os
import sys

from uvicorn.main import main as uvicorn_main

from pylon_service.settings import settings


def main() -> None:
    # TODO: Handling multiple workers would require:
    #   - moving DB migration from a worker startup to a server startup
    #   - ensuring that only one worker performs tasks rescheduling in its startup
    #     and the other wait for it to finish
    #   - prometheus instrumentation
    #   - the OpenTelemetry SDK (TracerProvider + BatchSpanProcessor's background exporter
    #     thread) is initialised once at module import and would not survive fork(), so multiple
    #     workers would lose spans and risk deadlocks; it would need per-worker post-fork setup
    if any(arg == "--workers" or arg.startswith("--workers=") for arg in sys.argv[1:]):
        raise RuntimeError("Passing --workers is not supported for pylon-service.")

    # uvicorn also reads the worker count from the WEB_CONCURRENCY environment variable (common in
    # container setups), which would silently fork workers without --workers ever being passed.
    web_concurrency = os.environ.get("WEB_CONCURRENCY")
    if web_concurrency is not None and web_concurrency.strip() not in ("", "1"):
        raise RuntimeError(
            f"WEB_CONCURRENCY={web_concurrency!r} is not supported for pylon-service; "
            "it must run as a single process (set WEB_CONCURRENCY=1 or leave it unset)."
        )

    host = os.environ.get("PYLON_UVICORN_HOST", "0.0.0.0")
    port = int(os.environ.get("PYLON_UVICORN_PORT", "8000"))
    auto_reload = settings.debug

    uvicorn_main(
        args=sys.argv[1:],
        prog_name="pylon-service",
        default_map={
            "app": "pylon_service.main:app",
            "host": host,
            "port": port,
            "reload": auto_reload,
        },
    )


if __name__ == "__main__":
    main()
