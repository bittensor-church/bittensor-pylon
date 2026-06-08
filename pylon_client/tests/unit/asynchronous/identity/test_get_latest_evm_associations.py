from http import HTTPMethod

import pytest
from httpx import Response, codes

from pylon_client._internal.pylon_commons._unstable.endpoints import Endpoint as EndpointUnstable
from pylon_client._internal.pylon_commons.types import EvmAddress
from pylon_client.artanis import BlockHash, BlockNumber, Hotkey
from pylon_client.artanis.unstable import (
    Block,
    EvmAssociation,
    GetLatestEvmAssociationsResponse,
)
from tests.unit.asynchronous.base_test import IdentityEndpointTest


class TestAsyncIdentityGetLatestEvmAssociations(IdentityEndpointTest):
    endpoint = EndpointUnstable.LATEST_EVM_ASSOCIATIONS
    route_params = {"identity_name": "sn1", "netuid": 1}
    http_method = HTTPMethod.GET

    async def make_endpoint_call(self, client):
        return await client.unstable.identity.get_latest_evm_associations()

    @pytest.fixture
    def block(self) -> Block:
        return Block(number=BlockNumber(1000), hash=BlockHash("0x123"))

    @pytest.fixture
    def success_response(self, block: Block) -> GetLatestEvmAssociationsResponse:
        evm_associations: dict[Hotkey, EvmAssociation] = {
            Hotkey("hotkey1"): EvmAssociation(
                hotkey=Hotkey("hotkey1"),
                evm_address=EvmAddress("0x1234567890123456789012345678901234567890"),
                last_block_where_ownership_was_proven=BlockNumber(999),
            ),
            Hotkey("hotkey2"): EvmAssociation(
                hotkey=Hotkey("hotkey2"),
                evm_address=EvmAddress("0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"),
                last_block_where_ownership_was_proven=BlockNumber(998),
            ),
        }
        return GetLatestEvmAssociationsResponse(block=block, evm_associations=evm_associations)

    @pytest.mark.asyncio
    async def test_success_with_no_evm_associations(self, pylon_client, service_mock, route_mock, block):
        self._setup_login_mock(service_mock)
        response_data = GetLatestEvmAssociationsResponse(block=block, evm_associations={})
        route_mock.mock(return_value=Response(status_code=codes.OK, json=response_data.model_dump(mode="json")))

        async with pylon_client:
            response = await pylon_client.unstable.identity.get_latest_evm_associations()

        assert response == response_data
