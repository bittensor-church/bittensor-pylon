import pytest

from pylon_client._internal.asynchronous.client import AsyncPylonClient
from pylon_client._internal.asynchronous.config import AsyncConfig
from pylon_client._internal.pylon_commons.types import PylonAuthToken


@pytest.fixture
def pylon_client_factory():
    def _create_client(address: str) -> AsyncPylonClient:
        config = AsyncConfig(
            address=address,
            open_access_token=PylonAuthToken("test_token"),
        )
        return AsyncPylonClient(config)

    return _create_client
