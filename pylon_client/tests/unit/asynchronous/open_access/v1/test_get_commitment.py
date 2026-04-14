from http import HTTPMethod

import pytest

from pylon_client._internal.pylon_commons.types import NetUid
from pylon_client._internal.pylon_commons.v1.endpoints import Endpoint as EndpointV1
from pylon_client.artanis import (
    BlockHash,
    BlockNumber,
    CommitmentDataHex,
    Hotkey,
)
from pylon_client.artanis.v1 import Block, GetCommitmentResponse
from tests.unit.asynchronous.base_test import OpenAccessEndpointTest


class TestAsyncOpenAccessGetCommitmentV1(OpenAccessEndpointTest):
    endpoint = EndpointV1.LATEST_COMMITMENTS_HOTKEY
    route_params = {"netuid": 1, "hotkey": "hotkey1"}
    http_method = HTTPMethod.GET

    async def make_endpoint_call(self, client):
        return await client.v1.open_access.get_commitment(netuid=NetUid(1), hotkey=Hotkey("hotkey1"))

    @pytest.fixture
    def success_response(self) -> GetCommitmentResponse:
        return GetCommitmentResponse(
            block=Block(number=BlockNumber(1000), hash=BlockHash("0x123")),
            hotkey=Hotkey("hotkey1"),
            commitment_block_number=BlockNumber(950),
            commitment=CommitmentDataHex("0xaabbccdd"),
        )
