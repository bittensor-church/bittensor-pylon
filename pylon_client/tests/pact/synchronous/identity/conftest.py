import pytest

from pylon_client._internal.pylon_commons.types import IdentityName, NetUid, PylonAuthToken
from pylon_client._internal.pylon_commons.v1.responses import IdentityLoginResponse
from pylon_client._internal.sync.client import PylonClient
from pylon_client._internal.sync.config import Config
from tests.pact.constants import IDENTITY_NAME, NETUID


@pytest.fixture
def pylon_client_factory():
    def _create_client(address: str, logged_in: bool = False) -> PylonClient:
        config = Config(
            address=address,
            identity_name=IdentityName(IDENTITY_NAME),
            identity_token=PylonAuthToken("test_identity_token"),
        )
        client = PylonClient(config)
        if logged_in:
            client.identity._login_response = IdentityLoginResponse(
                netuid=NetUid(NETUID),
                identity_name=IdentityName(IDENTITY_NAME),
            )
        return client

    return _create_client
