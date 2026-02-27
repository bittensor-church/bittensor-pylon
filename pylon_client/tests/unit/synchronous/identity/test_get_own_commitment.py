from http import HTTPMethod

import pytest

from pylon_client._internal.pylon_commons._unstable.endpoints import Endpoint as EndpointUnstable
from pylon_client.artanis import BlockHash, BlockNumber, CommitmentDataHex, Hotkey
from pylon_client.artanis.unstable import Block, GetCommitmentResponse
from tests.unit.synchronous.base_test import IdentityEndpointTest


class TestSyncIdentityGetOwnCommitment(IdentityEndpointTest):
    endpoint = EndpointUnstable.LATEST_COMMITMENTS_SELF
    route_params = {"identity_name": "sn1", "netuid": 1}
    http_method = HTTPMethod.GET

    def make_endpoint_call(self, client):
        return client.unstable.identity.get_own_commitment()

    @pytest.fixture
    def success_response(self) -> GetCommitmentResponse:
        return GetCommitmentResponse(
            block=Block(number=BlockNumber(1000), hash=BlockHash("0xabc123")),
            commitment_block_number=BlockNumber(950),
            hotkey=Hotkey("5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"),
            commitment=CommitmentDataHex("0xaabbccdd"),
        )
