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
    if any(arg == "--workers" or arg.startswith("--workers=") for arg in sys.argv[1:]):
        raise RuntimeError("Passing --workers is not supported for pylon-service.")

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
