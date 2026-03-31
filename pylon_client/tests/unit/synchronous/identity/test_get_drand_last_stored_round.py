from http import HTTPMethod

import pytest

from pylon_client._internal.pylon_commons._unstable.endpoints import Endpoint as EndpointUnstable
from pylon_client.artanis.unstable import GetDrandLastStoredRoundResponse
from tests.unit.synchronous.base_test import IdentityEndpointTest


class TestSyncOpenAccessGetDrandLastStoredRound(IdentityEndpointTest):
    endpoint = EndpointUnstable.DRAND_LAST_STORED_ROUND
    route_params = {}
    http_method = HTTPMethod.GET

    def make_endpoint_call(self, client):
        return client.unstable.identity.get_drand_last_stored_round()

    @pytest.fixture
    def success_response(self) -> GetDrandLastStoredRoundResponse:
        return GetDrandLastStoredRoundResponse(last_stored_round=123456)
