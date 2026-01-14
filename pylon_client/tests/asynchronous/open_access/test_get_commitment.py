from http import HTTPMethod

import pytest

from pylon_client._internal.pylon_commons.endpoints import Endpoint
from pylon_client._internal.pylon_commons.models import Block
from pylon_client._internal.pylon_commons.responses import GetCommitmentResponse
from pylon_client._internal.pylon_commons.types import BlockHash, BlockNumber, CommitmentDataHex, Hotkey, NetUid
from tests.asynchronous.base_test import OpenAccessEndpointTest


class TestAsyncOpenAccessGetCommitment(OpenAccessEndpointTest):
    endpoint = Endpoint.LATEST_COMMITMENTS_HOTKEY
    route_params = {"netuid": 1, "hotkey": "hotkey1"}
    http_method = HTTPMethod.GET

    async def make_endpoint_call(self, client):
        return await client.open_access.get_commitment(netuid=NetUid(1), hotkey=Hotkey("hotkey1"))

    @pytest.fixture
    def success_response(self) -> GetCommitmentResponse:
        return GetCommitmentResponse(
            block=Block(number=BlockNumber(1000), hash=BlockHash("0xabc123")),
            hotkey=Hotkey("hotkey1"),
            commitment=CommitmentDataHex("0xaabbccdd"),
        )
