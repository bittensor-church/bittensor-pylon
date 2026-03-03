"""
Pact test specific fixtures.
"""

from os import environ
from pathlib import Path

import pytest

from tests.helpers import UvicornServer


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
