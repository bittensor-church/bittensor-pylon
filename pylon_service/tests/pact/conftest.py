"""
Pact test specific fixtures.
"""

import threading
import time
from os import environ
from pathlib import Path

import pytest
import uvicorn


class UvicornServer:
    def __init__(self, app, host: str = "localhost", port: int = 58000):
        self.config = uvicorn.Config(app, host=host, port=port, log_level="debug")
        self.server = uvicorn.Server(self.config)
        self._thread: threading.Thread | None = None

    def start(self):
        self._thread = threading.Thread(target=self.server.run, daemon=True)
        self._thread.start()
        timeout_seconds = 5
        elapsed_seconds = 0.0
        while not self.server.started:
            time.sleep(0.1)
            elapsed_seconds += 0.1
            if elapsed_seconds >= timeout_seconds:
                self.stop()
                raise RuntimeError("Timeout while waiting for uvicorn server to start.")

    def stop(self):
        self.server.should_exit = True
        if self._thread:
            self._thread.join(timeout=5)


@pytest.fixture(scope="session")
def pacts_dir():
    from_env = environ.get("PACT_FILES_DIR")
    if from_env:
        return Path(from_env)
    return Path(__file__).parent.parent.parent.parent / "pylon_client" / "tests" / "pact" / "pacts"


@pytest.fixture(scope="session", autouse=True)
def ensure_pact_files_exist(pacts_dir: Path):
    if not pacts_dir.exists() or not list(pacts_dir.glob("*-pylon_service.json")):
        pytest.exit(
            f"No pact files found in: {pacts_dir}\n"
            "Run client pact tests first to generate pact files: cd pylon_client && nox -s test-pact",
            returncode=1,
        )


@pytest.fixture(scope="session")
def provider_host():
    return "localhost"


@pytest.fixture(scope="session")
def provider_port():
    return int(environ.get("PACT_PROVIDER_PORT", 58000))


@pytest.fixture(scope="session")
def provider_url(provider_host, provider_port):
    return f"http://{provider_host}:{provider_port}"


@pytest.fixture(scope="session")
def provider_server(test_app, provider_host, provider_port):
    server = UvicornServer(test_app, host=provider_host, port=provider_port)
    server.start()
    yield server
    server.stop()
