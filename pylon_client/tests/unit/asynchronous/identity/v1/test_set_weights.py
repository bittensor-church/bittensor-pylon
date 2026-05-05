from http import HTTPMethod

import pytest

from pylon_client._internal.pylon_commons.v1.endpoints import Endpoint
from pylon_client.artanis import Hotkey, Weight
from pylon_client.artanis.v1 import SetWeightsResponse
from tests.unit.asynchronous.base_test import IdentityEndpointTest


class TestIdentitySetWeights(IdentityEndpointTest):
    endpoint = Endpoint.SUBNET_WEIGHTS
    route_params = {"identity_name": "sn1", "netuid": 1}
    http_method = HTTPMethod.PUT

    async def make_endpoint_call(self, client):
        return await client.v1.identity.put_weights(weights={Hotkey("h1"): Weight(0.2)})

    @pytest.fixture
    def success_response(self) -> SetWeightsResponse:
        return SetWeightsResponse()
