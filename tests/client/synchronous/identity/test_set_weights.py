import json
from http import HTTPMethod

import pytest
from pydantic import ValidationError

from pylon_client._internal.common.endpoints import Endpoint
from pylon_client._internal.common.requests import SetWeightsRequest
from pylon_client._internal.common.responses import SetWeightsResponse
from pylon_client._internal.common.types import Hotkey, IdentityName, NetUid, Weight
from tests.client.synchronous.base_test import IdentityEndpointTest


class TestSyncIdentitySetWeights(IdentityEndpointTest):
    endpoint = Endpoint.SUBNET_WEIGHTS
    route_params = {"identity_name": "sn1", "netuid": 1}
    http_method = HTTPMethod.PUT

    def make_endpoint_call(self, client):
        return client.identity.put_weights(weights={Hotkey("h1"): Weight(0.2)})

    @pytest.fixture
    def success_response(self) -> SetWeightsResponse:
        return SetWeightsResponse()

    def test_success(self, pylon_client, service_mock, route_mock, success_response):
        super().test_success(pylon_client, service_mock, route_mock, success_response)
        assert json.loads(route_mock.calls.last.request.content) == {"weights": {"h1": 0.2}}


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
def test_sync_set_weights_request_validation_error(invalid_weights, expected_errors):
    """
    Test that SetWeightsRequest validates input correctly.
    """
    with pytest.raises(ValidationError) as exc_info:
        SetWeightsRequest(netuid=NetUid(1), identity_name=IdentityName("test"), weights=invalid_weights)

    errors = exc_info.value.errors(include_url=False, include_context=False, include_input=False)
    assert errors == expected_errors
