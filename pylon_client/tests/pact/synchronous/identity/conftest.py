import pytest

from pylon_client.artanis import Config, IdentityName, NetUid, PylonAuthToken, PylonClient
from tests.pact.constants import IDENTITY_NAME, IDENTITY_TOKEN, NETUID


@pytest.fixture
def pylon_client_factory():
    def _create_client(address: str, logged_in: bool = False) -> PylonClient:
        config = Config(
            address=address,
            identity_name=IdentityName(IDENTITY_NAME),
            identity_token=PylonAuthToken(IDENTITY_TOKEN),
        )
        client = PylonClient(config)
        if logged_in:
            client.unstable.identity._netuid = NetUid(NETUID)
            client.unstable.identity._identity_name = IdentityName(IDENTITY_NAME)
        return client

    return _create_client
