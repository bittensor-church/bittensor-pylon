from collections.abc import Generator
from pathlib import Path

import pytest
from pact import Pact


@pytest.fixture(scope="session")
def consumer_name() -> str:
    return "async_pylon_client"


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
