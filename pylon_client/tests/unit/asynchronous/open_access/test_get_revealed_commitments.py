from http import HTTPMethod

import pytest

from pylon_client._internal.pylon_commons._unstable.endpoints import Endpoint as EndpointUnstable
from pylon_client._internal.pylon_commons.types import NetUid, RevealedCommitmentData
from pylon_client.artanis import BlockHash, BlockNumber, Hotkey
from pylon_client.artanis.unstable import Block, GetRevealedCommitmentsResponse, RevealedCommitment
from tests.unit.asynchronous.base_test import OpenAccessEndpointTest


class TestAsyncOpenAccessGetRevealedCommitments(OpenAccessEndpointTest):
    endpoint = EndpointUnstable.LATEST_COMMITMENTS_REVEALED_HOTKEY
    route_params = {"netuid": 1, "hotkey": "hotkey1"}
    http_method = HTTPMethod.GET

    async def make_endpoint_call(self, client):
        return await client.unstable.open_access.get_revealed_commitments(netuid=NetUid(1), hotkey=Hotkey("hotkey1"))

    @pytest.fixture
    def success_response(self) -> GetRevealedCommitmentsResponse:
        return GetRevealedCommitmentsResponse(
            block=Block(number=BlockNumber(1000), hash=BlockHash("0xabc123")),
            commitments=[
                RevealedCommitment(
                    hotkey=Hotkey("hotkey1"),
                    reveal_block_number=BlockNumber(950),
                    commitment=RevealedCommitmentData("some revealed data"),
                )
            ],
        )
