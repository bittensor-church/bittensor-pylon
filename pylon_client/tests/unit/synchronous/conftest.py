import pytest
from tenacity import wait_none

from pylon_client.artanis import DEFAULT_RETRIES, Config, IdentityName, PylonAuthToken, PylonClient


@pytest.fixture
def sync_open_access_client(test_url):
    return PylonClient(
        Config(
            address=test_url,
            open_access_token=PylonAuthToken("open_access_token"),
            retry=DEFAULT_RETRIES.copy(wait=wait_none()),
        )
    )


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
