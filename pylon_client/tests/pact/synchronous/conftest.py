from collections.abc import Generator
from pathlib import Path

import pytest
from pact import Pact
from tenacity import stop_after_attempt

from pylon_client._internal.pylon_commons.timeout import PylonTimeout
from pylon_client._internal.pylon_commons.types import PylonAuthToken
from pylon_client._internal.sync.client import PylonClient
from pylon_client._internal.sync.config import DEFAULT_RETRIES, Config


@pytest.fixture(scope="session")
def consumer_name() -> str:
    return "sync_pylon_client"


@pytest.fixture(scope="session")
def provider_name() -> str:
    return "pylon_service"


@pytest.fixture
def pact(pacts_dir: Path, consumer_name: str, provider_name: str) -> Generator[Pact, None, None]:
    pact = Pact(consumer_name, provider_name).with_specification("V4")
    yield pact
    pact.write_file(pacts_dir)


@pytest.fixture(scope="session", autouse=True)
def remove_old_pact(pacts_dir: Path, consumer_name: str, provider_name: str):
    pact_file = pacts_dir / f"{consumer_name}-{provider_name}.json"
    pact_file.unlink(missing_ok=True)


@pytest.fixture
def pylon_client_factory():
    def _create_client(address: str) -> PylonClient:
        config = Config(
            address=address,
            open_access_token=PylonAuthToken("test_token"),
            timeout=PylonTimeout(read=0.5),
            retry=DEFAULT_RETRIES.copy(stop=stop_after_attempt(1)),
        )
        return PylonClient(config)

    return _create_client
