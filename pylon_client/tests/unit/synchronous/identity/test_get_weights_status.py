from http import HTTPMethod

import pytest

from pylon_client._internal.pylon_commons._unstable.endpoints import Endpoint as EndpointUnstable
from pylon_client.artanis import BlockNumber, MechanismId
from pylon_client.artanis.unstable import GetWeightsStatusResponse
from tests.unit.synchronous.base_test import IdentityEndpointTest


class TestSyncIdentityGetWeightsStatus(IdentityEndpointTest):
    endpoint = EndpointUnstable.SUBNET_MECHANISM_WEIGHTS_STATUS
    route_params = {"identity_name": "sn1", "netuid": 1, "mechanism_id": 1, "block_number": 123}
    http_method = HTTPMethod.GET

    def make_endpoint_call(self, client):
        return client.unstable.identity.get_weights_status(
            mechanism_id=MechanismId(1),
            block_number=BlockNumber(123),
        )

    @pytest.fixture
    def success_response(self) -> GetWeightsStatusResponse:
        return GetWeightsStatusResponse(weights_submitted=True)
