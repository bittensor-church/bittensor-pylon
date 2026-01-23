from http import HTTPMethod

import pytest

from pylon_client._internal.pylon_commons.endpoints import Endpoint
from pylon_client._internal.pylon_commons.models import Block
from pylon_client._internal.pylon_commons.responses import GetCommitmentResponse
from pylon_client._internal.pylon_commons.types import BlockHash, BlockNumber, CommitmentDataHex, Hotkey
from tests.unit.synchronous.base_test import IdentityEndpointTest


class TestSyncIdentityGetCommitment(IdentityEndpointTest):
    endpoint = Endpoint.LATEST_COMMITMENTS_HOTKEY
    route_params = {"identity_name": "sn1", "netuid": 1, "hotkey": "hotkey1"}
    http_method = HTTPMethod.GET

    def make_endpoint_call(self, client):
        return client.identity.get_commitment(hotkey=Hotkey("hotkey1"))

    @pytest.fixture
    def success_response(self) -> GetCommitmentResponse:
        return GetCommitmentResponse(
            block=Block(number=BlockNumber(1000), hash=BlockHash("0xabc123")),
            hotkey=Hotkey("hotkey1"),
            commitment=CommitmentDataHex("0xaabbccdd"),
        )
