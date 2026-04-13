from http import HTTPMethod

import pytest

from pylon_client._internal.pylon_commons._unstable.endpoints import Endpoint as EndpointUnstable
from pylon_client._internal.pylon_commons.types import RevealedCommitmentData
from pylon_client.artanis import BlockHash, BlockNumber, Hotkey
from pylon_client.artanis.unstable import Block, GetAllRevealedCommitmentsResponse, RevealedCommitment
from tests.unit.asynchronous.base_test import IdentityEndpointTest


class TestAsyncIdentityGetAllRevealedCommitments(IdentityEndpointTest):
    endpoint = EndpointUnstable.LATEST_COMMITMENTS_REVEALED
    route_params = {"identity_name": "sn1", "netuid": 1}
    http_method = HTTPMethod.GET

    async def make_endpoint_call(self, client):
        return await client.unstable.identity.get_all_revealed_commitments()

    @pytest.fixture
    def success_response(self) -> GetAllRevealedCommitmentsResponse:
        return GetAllRevealedCommitmentsResponse(
            block=Block(number=BlockNumber(1000), hash=BlockHash("0xabc123")),
            commitments={
                Hotkey("hotkey1"): [
                    RevealedCommitment(
                        hotkey=Hotkey("hotkey1"),
                        reveal_block_number=BlockNumber(950),
                        commitment=RevealedCommitmentData("some revealed data"),
                    )
                ]
            },
        )
