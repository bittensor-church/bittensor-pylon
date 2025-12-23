import pytest
from httpx import ConnectTimeout, Response, codes
from tenacity import stop_after_attempt

from pylon_client._internal.client.asynchronous.client import AsyncPylonClient
from pylon_client._internal.client.asynchronous.config import ASYNC_DEFAULT_RETRIES, AsyncConfig
from pylon_client._internal.common.endpoints import Endpoint
from pylon_client._internal.common.exceptions import PylonRequestException
from pylon_client._internal.common.responses import SetWeightsResponse
from pylon_client._internal.common.types import Hotkey, IdentityName, PylonAuthToken, Weight
from pylon_client.service.main import app


@pytest.mark.parametrize(
    "attempts",
    (
        pytest.param(2, id="two_attempts"),
        pytest.param(4, id="four_attempts"),
    ),
)
@pytest.mark.asyncio
async def test_async_config_retries_success(service_mock, test_url, attempts):
    """
    Test that client retries the specified number of times before succeeding.
    """
    login_url = app.route_reverse(Endpoint.IDENTITY_LOGIN.reverse, identity_name="sn1")
    weights_url = app.route_reverse(Endpoint.SUBNET_WEIGHTS.reverse, identity_name="sn1", netuid=1)

    login_response_json = {"netuid": 1, "identity_name": "sn1"}
    service_mock.post(login_url).mock(return_value=Response(status_code=codes.OK, json=login_response_json))
    route = service_mock.put(weights_url)
    route.mock(
        side_effect=[
            *(ConnectTimeout("Connection timed out") for i in range(attempts - 1)),
            Response(
                status_code=codes.OK,
                json={
                    "detail": "weights update scheduled",
                    "count": 1,
                },
            ),
        ]
    )
    async with AsyncPylonClient(
        AsyncConfig(
            address=test_url,
            identity_name=IdentityName("sn1"),
            identity_token=PylonAuthToken("test_token"),
            retry=ASYNC_DEFAULT_RETRIES.copy(stop=stop_after_attempt(attempts)),
        )
    ) as async_client:
        response = await async_client.identity.put_weights(weights={Hotkey("h2"): Weight(0.1)})
    assert response == SetWeightsResponse()
    assert route.call_count == attempts


@pytest.mark.asyncio
async def test_async_config_retries_error(service_mock, test_url):
    """
    Test that client raises PylonRequestException after all retries exhausted.
    """
    login_url = app.route_reverse(Endpoint.IDENTITY_LOGIN.reverse, identity_name="sn1")
    weights_url = app.route_reverse(Endpoint.SUBNET_WEIGHTS.reverse, identity_name="sn1", netuid=1)

    login_response_json = {"netuid": 1, "identity_name": "sn1"}
    service_mock.post(login_url).mock(return_value=Response(status_code=codes.OK, json=login_response_json))
    route = service_mock.put(weights_url)
    route.mock(side_effect=ConnectTimeout("Connection timed out"))
    async with AsyncPylonClient(
        AsyncConfig(
            address=test_url,
            identity_name=IdentityName("sn1"),
            identity_token=PylonAuthToken("test_token"),
            # Check if reraise will be forced to True.
            retry=ASYNC_DEFAULT_RETRIES.copy(stop=stop_after_attempt(2), reraise=False),
        )
    ) as async_client:
        with pytest.raises(PylonRequestException):
            await async_client.identity.put_weights(weights={Hotkey("h2"): Weight(0.1)})
    assert route.call_count == 2
