import pytest
from httpx import ConnectError, Response, codes
from tenacity import stop_after_attempt

from pylon_client._internal.pylon_commons._unstable.endpoints import Endpoint as EndpointUnstable
from pylon_client._internal.pylon_commons.types import MechanismId
from pylon_client.artanis import (
    DEFAULT_RETRIES,
    Config,
    Hotkey,
    IdentityName,
    NetUid,
    PylonAuthToken,
    PylonClient,
    PylonRequestException,
    Weight,
)
from pylon_client.artanis.unstable import SetWeightsResponse


@pytest.mark.parametrize(
    "attempts",
    (
        pytest.param(2, id="two_attempts"),
        pytest.param(4, id="four_attempts"),
    ),
)
def test_sync_config_retries_success(service_mock, test_url, attempts):
    """
    Test that client retries the specified number of times before succeeding.
    """
    identities_url = EndpointUnstable.IDENTITIES.absolute_url()
    weights_url = EndpointUnstable.SUBNET_MECHANISMS_WEIGHTS.absolute_url(
        identity_name_=IdentityName("sn1"), netuid_=NetUid(1), mechanism_id=MechanismId(0)
    )

    identities_response_json = {"identities": {"sn1": 1}}
    service_mock.get(identities_url).mock(return_value=Response(status_code=codes.OK, json=identities_response_json))
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
    with PylonClient(
        Config(
            address=test_url,
            identity_name=IdentityName("sn1"),
            identity_token=PylonAuthToken("test_token"),
            retry=DEFAULT_RETRIES.copy(stop=stop_after_attempt(attempts)),
        )
    ) as sync_client:
        response = sync_client.unstable.identity.put_weights(weights={Hotkey("h2"): Weight(0.1)})
    assert response == SetWeightsResponse()
    assert route.call_count == attempts


def test_sync_config_retries_error(service_mock, test_url):
    """
    Test that client raises PylonRequestException after all retries exhausted.
    """
    identities_url = EndpointUnstable.IDENTITIES.absolute_url()
    weights_url = EndpointUnstable.SUBNET_MECHANISMS_WEIGHTS.absolute_url(
        identity_name_=IdentityName("sn1"), netuid_=NetUid(1), mechanism_id=MechanismId(0)
    )

    identities_response_json = {"identities": {"sn1": 1}}
    service_mock.get(identities_url).mock(return_value=Response(status_code=codes.OK, json=identities_response_json))
    route = service_mock.put(weights_url)
    route.mock(side_effect=ConnectError("Connection failed"))
    with PylonClient(
        Config(
            address=test_url,
            identity_name=IdentityName("sn1"),
            identity_token=PylonAuthToken("test_token"),
            retry=DEFAULT_RETRIES.copy(stop=stop_after_attempt(2), reraise=False),
        )
    ) as sync_client:
        with pytest.raises(PylonRequestException):
            sync_client.unstable.identity.put_weights(weights={Hotkey("h2"): Weight(0.1)})
    assert route.call_count == 2
