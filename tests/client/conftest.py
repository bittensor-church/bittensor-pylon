import pytest
import respx
from tenacity import wait_none

from pylon._internal.client.asynchronous import AsyncPylonClient
from pylon._internal.client.config import DEFAULT_RETRIES, AsyncConfig
from pylon._internal.common.types import IdentityName, PylonAuthToken


@pytest.fixture
def test_url():
    return "http://testserver:8080"


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
            retry=DEFAULT_RETRIES.copy(wait=wait_none()),
        )
    )


@pytest.fixture
def async_client(test_url):
    return AsyncPylonClient(
        AsyncConfig(
            address=test_url,
            open_access_token=PylonAuthToken("open_access_token"),
            identity_name=IdentityName("sn1"),
            identity_token=PylonAuthToken("sn1_token"),
            retry=DEFAULT_RETRIES.copy(wait=wait_none()),
        )
    )


@pytest.fixture
def client_no_credentials(test_url):
    return AsyncPylonClient(AsyncConfig(address=test_url))


@pytest.fixture
def service_mock(test_url):
    with respx.mock(base_url=test_url) as respx_mock:
        yield respx_mock
