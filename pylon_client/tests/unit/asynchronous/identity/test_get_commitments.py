from http import HTTPMethod

import pytest
from httpx import Response, codes

from pylon_client._internal.pylon_commons._unstable.endpoints import Endpoint as EndpointUnstable
from pylon_client.artanis import BlockHash, BlockNumber, CommitmentDataHex, Hotkey
from pylon_client.artanis.unstable import (
    Block,
    CommitmentVariant,
    GetCommitmentsResponse,
    HexDataCommitment,
)
from tests.unit.asynchronous.base_test import IdentityEndpointTest


class TestAsyncIdentityGetCommitments(IdentityEndpointTest):
    endpoint = EndpointUnstable.LATEST_COMMITMENTS
    route_params = {"identity_name": "sn1", "netuid": 1}
    http_method = HTTPMethod.GET

    async def make_endpoint_call(self, client):
        return await client.unstable.identity.get_commitments()

    @pytest.fixture
    def block(self) -> Block:
        return Block(number=BlockNumber(1000), hash=BlockHash("0x123"))

    @pytest.fixture
    def success_response(self, block: Block) -> GetCommitmentsResponse:
        commitments: dict[Hotkey, CommitmentVariant] = {
            Hotkey("hotkey1"): HexDataCommitment(
                commitment_block_number=BlockNumber(999),
                hotkey=Hotkey("hotkey1"),
                commitment=CommitmentDataHex("0xaabbccdd"),
            ),
            Hotkey("hotkey2"): HexDataCommitment(
                commitment_block_number=BlockNumber(999),
                hotkey=Hotkey("hotkey2"),
                commitment=CommitmentDataHex("0x11223344"),
            ),
        }
        return GetCommitmentsResponse(block=block, commitments=commitments)

    @pytest.mark.asyncio
    async def test_success_with_empty_commitments(self, pylon_client, service_mock, route_mock, block):
        self._setup_login_mock(service_mock)
        response_data = GetCommitmentsResponse(block=block, commitments={})
        route_mock.mock(return_value=Response(status_code=codes.OK, json=response_data.model_dump(mode="json")))

        async with pylon_client:
            response = await pylon_client.unstable.identity.get_commitments()

        assert response == response_data
