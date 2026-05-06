from http import HTTPMethod

import pytest

from pylon_client._internal.pylon_commons.v1.endpoints import Endpoint as EndpointUnstable
from pylon_client.artanis import Hotkey, Weight
from pylon_client.artanis.v1 import SetWeightsResponse
from tests.unit.synchronous.base_test import IdentityEndpointTest


class TestSyncIdentitySetWeights(IdentityEndpointTest):
    endpoint = EndpointUnstable.SUBNET_WEIGHTS
    route_params = {"identity_name": "sn1", "netuid": 1}
    http_method = HTTPMethod.PUT

    def make_endpoint_call(self, client):
        return client.v1.identity.put_weights(weights={Hotkey("h1"): Weight(0.2)})

    @pytest.fixture
    def success_response(self) -> SetWeightsResponse:
        return SetWeightsResponse()
