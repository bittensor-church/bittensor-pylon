import pytest
from tenacity import wait_none

from pylon_client.artanis import ASYNC_DEFAULT_RETRIES, AsyncConfig, AsyncPylonClient, IdentityName, PylonAuthToken


@pytest.fixture
def open_access_client(test_url):
    return AsyncPylonClient(
        AsyncConfig(
            address=test_url,
            open_access_token=PylonAuthToken("open_access_token"),
            retry=ASYNC_DEFAULT_RETRIES.copy(wait=wait_none()),
        )
    )


@pytest.fixture
def identity_client(test_url):
    return AsyncPylonClient(
        AsyncConfig(
            address=test_url,
            identity_name=IdentityName("sn1"),
            identity_token=PylonAuthToken("sn1_token"),
            retry=ASYNC_DEFAULT_RETRIES.copy(wait=wait_none()),
        )
    )


@pytest.fixture
def pylon_client(test_url):
    return AsyncPylonClient(
        AsyncConfig(
            address=test_url,
            open_access_token=PylonAuthToken("open_access_token"),
            identity_name=IdentityName("sn1"),
            identity_token=PylonAuthToken("sn1_token"),
            retry=ASYNC_DEFAULT_RETRIES.copy(wait=wait_none()),
        )
    )


@pytest.fixture
def client_no_credentials(test_url):
    return AsyncPylonClient(AsyncConfig(address=test_url))
