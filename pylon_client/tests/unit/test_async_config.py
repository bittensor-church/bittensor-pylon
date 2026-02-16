import pytest
from httpx import ConnectError, Response, codes
from tenacity import stop_after_attempt

from pylon_client._internal.asynchronous.client import AsyncPylonClient
from pylon_client._internal.asynchronous.config import ASYNC_DEFAULT_RETRIES, AsyncConfig
from pylon_client._internal.pylon_commons.exceptions import PylonRequestException
from pylon_client._internal.pylon_commons.types import Hotkey, IdentityName, NetUid, PylonAuthToken, Weight
from pylon_client._internal.pylon_commons.v1.endpoints import Endpoint as EndpointV1
from pylon_client._internal.pylon_commons.v1.responses import SetWeightsResponse


@pytest.mark.parametrize(
    "attempts",
    (
        pytest.param(2, id="two_attempts"),
        pytest.param(4, id="four_attempts"),
    ),
)
@pytest.mark.asyncio
async def test_async_config_retries_success(service_mock, test_url, attempts):
    login_url = EndpointV1.IDENTITY_LOGIN.absolute_url(identity_name="sn1")
    weights_url = EndpointV1.SUBNET_WEIGHTS.absolute_url(identity_name_=IdentityName("sn1"), netuid_=NetUid(1))

    login_response_json = {"netuid": 1, "identity_name": "sn1"}
    service_mock.post(login_url).mock(return_value=Response(status_code=codes.OK, json=login_response_json))
    route = service_mock.put(weights_url)
    route.mock(
        side_effect=[
            *(ConnectError("Connection failed") for i in range(attempts - 1)),
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
    login_url = EndpointV1.IDENTITY_LOGIN.absolute_url(identity_name="sn1")
    weights_url = EndpointV1.SUBNET_WEIGHTS.absolute_url(identity_name_=IdentityName("sn1"), netuid_=NetUid(1))

    login_response_json = {"netuid": 1, "identity_name": "sn1"}
    service_mock.post(login_url).mock(return_value=Response(status_code=codes.OK, json=login_response_json))
    route = service_mock.put(weights_url)
    route.mock(side_effect=ConnectError("Connection failed"))
    async with AsyncPylonClient(
        AsyncConfig(
            address=test_url,
            identity_name=IdentityName("sn1"),
            identity_token=PylonAuthToken("test_token"),
            retry=ASYNC_DEFAULT_RETRIES.copy(stop=stop_after_attempt(2), reraise=False),
        )
    ) as async_client:
        with pytest.raises(PylonRequestException):
            await async_client.identity.put_weights(weights={Hotkey("h2"): Weight(0.1)})
    assert route.call_count == 2
