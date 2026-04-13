from http import HTTPMethod

import pytest

from pylon_client._internal.pylon_commons._unstable.endpoints import Endpoint as EndpointUnstable
from pylon_client.artanis.unstable import SetRevealedCommitmentResponse
from tests.unit.synchronous.base_test import IdentityEndpointTest


class TestSyncIdentitySetRevealedCommitment(IdentityEndpointTest):
    endpoint = EndpointUnstable.REVEALED_COMMITMENTS
    route_params = {"identity_name": "sn1", "netuid": 1}
    http_method = HTTPMethod.POST

    def make_endpoint_call(self, client):
        return client.unstable.identity.set_revealed_commitment(commitment="some secret data")

    @pytest.fixture
    def success_response(self) -> SetRevealedCommitmentResponse:
        return SetRevealedCommitmentResponse(reveal_round=123)
