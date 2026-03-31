from http import HTTPMethod

import pytest

from pylon_client._internal.pylon_commons._unstable.endpoints import Endpoint as EndpointUnstable
from pylon_client.artanis.unstable import GetDrandLastStoredRoundResponse
from tests.unit.asynchronous.base_test import OpenAccessEndpointTest


class TestAsyncOpenAccessGetDrandLastStoredRound(OpenAccessEndpointTest):
    endpoint = EndpointUnstable.DRAND_LAST_STORED_ROUND
    route_params = {}
    http_method = HTTPMethod.GET

    async def make_endpoint_call(self, client):
        return await client.unstable.open_access.get_drand_last_stored_round()

    @pytest.fixture
    def success_response(self) -> GetDrandLastStoredRoundResponse:
        return GetDrandLastStoredRoundResponse(last_stored_round=123456)
