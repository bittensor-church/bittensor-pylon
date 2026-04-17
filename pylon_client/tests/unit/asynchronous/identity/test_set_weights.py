import json
from http import HTTPMethod

import pytest
from httpx import Response, codes
from pydantic import ValidationError

from pylon_client._internal.pylon_commons._unstable.endpoints import Endpoint as EndpointUnstable
from pylon_client._internal.pylon_commons.v1.requests import SetWeightsRequest
from pylon_client.artanis import Hotkey, IdentityName, MechanismId, NetUid, Weight
from pylon_client.artanis.unstable import SetWeightsResponse
from tests.unit.asynchronous.base_test import IdentityEndpointTest


class TestIdentitySetWeights(IdentityEndpointTest):
    endpoint = EndpointUnstable.SUBNET_WEIGHTS
    route_params = {"identity_name": "sn1", "netuid": 1}
    http_method = HTTPMethod.PUT

    async def make_endpoint_call(self, client):
        return await client.unstable.identity.put_weights(weights={Hotkey("h1"): Weight(0.2)})

    async def test_put_weights(self, pylon_client, service_mock, route_mock_factory, success_response):
        self._setup_login_mock(service_mock)
        route_mock = route_mock_factory()
        route_mock.mock(return_value=Response(status_code=codes.OK, json=success_response.model_dump(mode="json")))

        async with pylon_client:
            response = await pylon_client.unstable.identity.put_weights(weights={Hotkey("h1"): Weight(0.2)})

        assert response == success_response
        assert service_mock.calls.last.request.url.path.endswith("/weights")
        assert json.loads(route_mock.calls.last.request.content) == {"weights": {"h1": 0.2}}

    async def test_put_weights_with_mechanism_id(
        self, pylon_client, service_mock, route_mock_factory, success_response
    ):
        self._setup_login_mock(service_mock)
        route_mock = route_mock_factory(
            endpoint=EndpointUnstable.SUBNET_MECHANISMS_WEIGHTS,
            extra_params={"mechanism_id": 1},
        )
        route_mock.mock(return_value=Response(status_code=codes.OK, json=success_response.model_dump(mode="json")))

        async with pylon_client:
            response = await pylon_client.unstable.identity.put_weights(
                weights={Hotkey("h1"): Weight(0.2)}, mechanism_id=MechanismId(1)
            )

        assert response == success_response
        assert service_mock.calls.last.request.url.path.endswith("/mechanism/1/weights")
        assert json.loads(route_mock.calls.last.request.content) == {"weights": {"h1": 0.2}}

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
