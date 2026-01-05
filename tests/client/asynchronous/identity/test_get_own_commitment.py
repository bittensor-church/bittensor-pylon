from http import HTTPMethod

import pytest

from pylon_client._internal.common.endpoints import Endpoint
from pylon_client._internal.common.models import Block
from pylon_client._internal.common.responses import GetCommitmentResponse
from pylon_client._internal.common.types import BlockHash, BlockNumber, CommitmentDataHex, Hotkey
from tests.client.asynchronous.base_test import IdentityEndpointTest


class TestAsyncIdentityGetOwnCommitment(IdentityEndpointTest):
    endpoint = Endpoint.LATEST_COMMITMENTS_SELF
    route_params = {"identity_name": "sn1", "netuid": 1}
    http_method = HTTPMethod.GET

    async def make_endpoint_call(self, client):
        return await client.identity.get_own_commitment()

    @pytest.fixture
    def success_response(self) -> GetCommitmentResponse:
        return GetCommitmentResponse(
            block=Block(number=BlockNumber(1000), hash=BlockHash("0xabc123")),
            hotkey=Hotkey("5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"),
            commitment=CommitmentDataHex("0xaabbccdd"),
        )
