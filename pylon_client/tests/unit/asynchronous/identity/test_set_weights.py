from http import HTTPMethod

import pytest
from pydantic import ValidationError

from pylon_client._internal.pylon_commons.types import Hotkey, IdentityName, NetUid, Weight
from pylon_client._internal.pylon_commons.v1.endpoints import Endpoint as EndpointV1
from pylon_client._internal.pylon_commons.v1.requests import SetWeightsRequest
from pylon_client._internal.pylon_commons.v1.responses import SetWeightsResponse
from tests.unit.asynchronous.base_test import IdentityEndpointTest


class TestIdentitySetWeights(IdentityEndpointTest):
    endpoint = EndpointV1.SUBNET_WEIGHTS
    route_params = {"identity_name": "sn1", "netuid": 1}
    http_method = HTTPMethod.PUT

    async def make_endpoint_call(self, client):
        return await client.identity.put_weights(weights={Hotkey("h1"): Weight(0.2)})

    @pytest.fixture
    def success_response(self) -> SetWeightsResponse:
        return SetWeightsResponse()


@pytest.mark.parametrize(
    "invalid_weights,expected_errors",
    [
        pytest.param(
            {},
            [{"type": "value_error", "loc": ("weights",), "msg": "Value error, No weights provided"}],
            id="empty_weights",
        ),
        pytest.param(
            {"": 0.5},
            [
                {
                    "type": "value_error",
                    "loc": ("weights",),
                    "msg": "Value error, Invalid hotkey: '' must be a non-empty string",
                }
            ],
            id="empty_hotkey",
        ),
        pytest.param(
            {"hotkey1": "invalid"},
            [
                {
                    "type": "float_parsing",
                    "loc": ("weights", "hotkey1"),
                    "msg": "Input should be a valid number, unable to parse string as a number",
                }
            ],
            id="non_numeric_weight",
        ),
        pytest.param(
            {"hotkey1": [0.5]},
            [{"type": "float_type", "loc": ("weights", "hotkey1"), "msg": "Input should be a valid number"}],
            id="list_weight",
        ),
    ],
)
def test_set_weights_request_validation_error(invalid_weights, expected_errors):
    """
    Test that SetWeightsRequest validates input correctly.
    """
    with pytest.raises(ValidationError) as exc_info:
        SetWeightsRequest(netuid=NetUid(1), identity_name=IdentityName("test"), weights=invalid_weights)

    errors = exc_info.value.errors(include_url=False, include_context=False, include_input=False)
    assert errors == expected_errors
