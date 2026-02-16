import pytest

from pylon_client._internal.asynchronous.client import AsyncPylonClient
from pylon_client._internal.asynchronous.config import AsyncConfig
from pylon_client._internal.pylon_commons.types import IdentityName, NetUid, PylonAuthToken
from pylon_client._internal.pylon_commons.v1.responses import IdentityLoginResponse
from tests.pact.constants import IDENTITY_NAME, NETUID


@pytest.fixture
def pylon_client_factory():
    def _create_client(address: str, logged_in: bool = False) -> AsyncPylonClient:
        config = AsyncConfig(
            address=address,
            identity_name=IdentityName(IDENTITY_NAME),
            identity_token=PylonAuthToken("test_identity_token"),
        )
        client = AsyncPylonClient(config)
        if logged_in:
            client.identity._login_response = IdentityLoginResponse(
                netuid=NetUid(NETUID),
                identity_name=IdentityName(IDENTITY_NAME),
            )
        return client

    return _create_client
