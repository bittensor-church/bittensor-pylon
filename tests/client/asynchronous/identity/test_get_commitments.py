from http import HTTPMethod

import pytest
from httpx import Response, codes

from pylon_client._internal.common.endpoints import Endpoint
from pylon_client._internal.common.models import Block
from pylon_client._internal.common.responses import GetCommitmentsResponse
from pylon_client._internal.common.types import BlockHash, BlockNumber, CommitmentDataHex, Hotkey
from tests.client.asynchronous.base_test import IdentityEndpointTest


class TestAsyncIdentityGetCommitments(IdentityEndpointTest):
    endpoint = Endpoint.LATEST_COMMITMENTS
    route_params = {"identity_name": "sn1", "netuid": 1}
    http_method = HTTPMethod.GET

    async def make_endpoint_call(self, client):
        return await client.identity.get_commitments()

    @pytest.fixture
    def block(self) -> Block:
        return Block(number=BlockNumber(1000), hash=BlockHash("0x123"))

    @pytest.fixture
    def success_response(self, block: Block) -> GetCommitmentsResponse:
        commitments = {
            Hotkey("hotkey1"): CommitmentDataHex("0xaabbccdd"),
            Hotkey("hotkey2"): CommitmentDataHex("0x11223344"),
        }
        return GetCommitmentsResponse(block=block, commitments=commitments)

    @pytest.mark.asyncio
    async def test_success_with_empty_commitments(self, pylon_client, service_mock, route_mock, block):
        self._setup_login_mock(service_mock)
        response_data = GetCommitmentsResponse(block=block, commitments={})
        route_mock.mock(return_value=Response(status_code=codes.OK, json=response_data.model_dump(mode="json")))

        async with pylon_client:
            response = await pylon_client.identity.get_commitments()

        assert response == response_data
