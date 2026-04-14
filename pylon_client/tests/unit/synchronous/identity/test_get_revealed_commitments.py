from http import HTTPMethod

import pytest

from pylon_client._internal.pylon_commons._unstable.endpoints import Endpoint as EndpointUnstable
from pylon_client._internal.pylon_commons.types import RevealedCommitmentData
from pylon_client.artanis import BlockHash, BlockNumber, Hotkey
from pylon_client.artanis.unstable import Block, GetRevealedCommitmentsResponse, RevealedCommitment
from tests.unit.synchronous.base_test import IdentityEndpointTest


class TestSyncIdentityGetRevealedCommitments(IdentityEndpointTest):
    endpoint = EndpointUnstable.LATEST_COMMITMENTS_REVEALED_HOTKEY
    route_params = {"identity_name": "sn1", "netuid": 1, "hotkey": "hotkey1"}
    http_method = HTTPMethod.GET

    def make_endpoint_call(self, client):
        return client.unstable.identity.get_revealed_commitments(hotkey=Hotkey("hotkey1"))

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
