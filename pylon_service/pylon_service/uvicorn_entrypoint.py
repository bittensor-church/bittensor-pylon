from __future__ import annotations

import os
import sys

from uvicorn.main import main as uvicorn_main

from pylon_service.settings import settings


def main() -> None:
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
