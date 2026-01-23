import pytest

from pylon_client._internal.pylon_commons.types import PylonAuthToken
from pylon_client._internal.sync.client import PylonClient
from pylon_client._internal.sync.config import Config


@pytest.fixture
def pylon_client_factory():
    def _create_client(address: str) -> PylonClient:
        config = Config(
            address=address,
            open_access_token=PylonAuthToken("test_token"),
        )
        return PylonClient(config)

    return _create_client
