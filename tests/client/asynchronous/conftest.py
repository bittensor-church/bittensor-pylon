import pytest
from tenacity import wait_none

from pylon_client._internal.client.asynchronous.client import AsyncPylonClient
from pylon_client._internal.client.asynchronous.config import ASYNC_DEFAULT_RETRIES, AsyncConfig
from pylon_client._internal.common.types import IdentityName, PylonAuthToken


@pytest.fixture
def open_access_client(test_url):
    return AsyncPylonClient(AsyncConfig(address=test_url, open_access_token=PylonAuthToken("open_access_token")))


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
