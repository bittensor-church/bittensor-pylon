import pytest

from pylon_client.artanis import AsyncConfig, AsyncPylonClient, IdentityName, NetUid, PylonAuthToken
from tests.pact.constants import IDENTITY_NAME, IDENTITY_TOKEN, NETUID


@pytest.fixture
def pylon_client_factory():
    def _create_client(address: str, logged_in: bool = False) -> AsyncPylonClient:
        config = AsyncConfig(
            address=address,
            identity_name=IdentityName(IDENTITY_NAME),
            identity_token=PylonAuthToken(IDENTITY_TOKEN),
        )
        client = AsyncPylonClient(config)
        if logged_in:
            client.v1.identity._netuid = NetUid(NETUID)
            client.v1.identity._identity_name = IdentityName(IDENTITY_NAME)
        return client

    return _create_client
