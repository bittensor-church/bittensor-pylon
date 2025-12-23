import pytest
from tenacity import wait_none

from pylon_client._internal.client.sync.client import PylonClient
from pylon_client._internal.client.sync.config import DEFAULT_RETRIES, Config
from pylon_client._internal.common.types import IdentityName, PylonAuthToken


@pytest.fixture
def sync_open_access_client(test_url):
    return PylonClient(Config(address=test_url, open_access_token=PylonAuthToken("open_access_token")))


@pytest.fixture
def sync_identity_client(test_url):
    return PylonClient(
        Config(
            address=test_url,
            identity_name=IdentityName("sn1"),
            identity_token=PylonAuthToken("sn1_token"),
            retry=DEFAULT_RETRIES.copy(wait=wait_none()),
        )
    )


@pytest.fixture
def sync_client(test_url):
    return PylonClient(
        Config(
            address=test_url,
            open_access_token=PylonAuthToken("open_access_token"),
            identity_name=IdentityName("sn1"),
            identity_token=PylonAuthToken("sn1_token"),
            retry=DEFAULT_RETRIES.copy(wait=wait_none()),
        )
    )


@pytest.fixture
def sync_client_no_credentials(test_url):
    return PylonClient(Config(address=test_url))
