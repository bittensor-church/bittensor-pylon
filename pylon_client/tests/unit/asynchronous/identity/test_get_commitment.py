from http import HTTPMethod

import pytest

from pylon_client._internal.pylon_commons.models import Block
from pylon_client._internal.pylon_commons.types import BlockHash, BlockNumber, CommitmentDataHex, Hotkey
from pylon_client._internal.pylon_commons.v1.endpoints import Endpoint as EndpointV1
from pylon_client._internal.pylon_commons.v1.responses import GetCommitmentResponse
from tests.unit.asynchronous.base_test import IdentityEndpointTest


class TestAsyncIdentityGetCommitment(IdentityEndpointTest):
    endpoint = EndpointV1.LATEST_COMMITMENTS_HOTKEY
    route_params = {"identity_name": "sn1", "netuid": 1, "hotkey": "hotkey1"}
    http_method = HTTPMethod.GET

    async def make_endpoint_call(self, client):
        return await client.identity.get_commitment(hotkey=Hotkey("hotkey1"))

    @pytest.fixture
    def success_response(self) -> GetCommitmentResponse:
        return GetCommitmentResponse(
            block=Block(number=BlockNumber(1000), hash=BlockHash("0xabc123")),
            commitment_block_number=BlockNumber(950),
            hotkey=Hotkey("hotkey1"),
            commitment=CommitmentDataHex("0xaabbccdd"),
        )
