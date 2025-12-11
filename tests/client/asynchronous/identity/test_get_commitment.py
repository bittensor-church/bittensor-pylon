from http import HTTPMethod

import pytest
from httpx import Response, codes

from pylon._internal.common.endpoints import Endpoint
from pylon._internal.common.responses import GetCommitmentResponse
from pylon._internal.common.types import CommitmentDataHex, Hotkey
from tests.client.asynchronous.base_test import IdentityEndpointTest


class TestAsyncIdentityGetCommitment(IdentityEndpointTest):
    endpoint = Endpoint.LATEST_COMMITMENTS_HOTKEY
    route_params = {"identity_name": "sn1", "netuid": 1, "hotkey": "hotkey1"}
    http_method = HTTPMethod.GET

    async def make_endpoint_call(self, client):
        return await client.identity.get_commitment(hotkey=Hotkey("hotkey1"))

    @pytest.fixture
    def success_response(self) -> GetCommitmentResponse:
        return GetCommitmentResponse(hotkey=Hotkey("hotkey1"), data=CommitmentDataHex("0xaabbccdd"))

    @pytest.mark.asyncio
    async def test_success_with_none_commitment(self, pylon_client, service_mock, route_mock):
        """
        Test getting a commitment when commitment data is None (not found).
        """
        self._setup_login_mock(service_mock)
        response_data = GetCommitmentResponse(hotkey=Hotkey("hotkey1"), data=None)
        route_mock.mock(return_value=Response(status_code=codes.OK, json=response_data.model_dump(mode="json")))

        async with pylon_client:
            response = await pylon_client.identity.get_commitment(hotkey=Hotkey("hotkey1"))

        assert response == response_data
