from http import HTTPMethod

import pytest
from httpx import Response, codes

from pylon_client._internal.pylon_commons._unstable.endpoints import Endpoint as EndpointUnstable
from pylon_client._internal.pylon_commons.types import EvmAddress
from pylon_client.artanis import BlockHash, BlockNumber, Hotkey, NetUid
from pylon_client.artanis.unstable import (
    Block,
    EvmAssociation,
    GetLatestEvmAssociationsResponse,
)
from tests.unit.synchronous.base_test import OpenAccessEndpointTest


class TestSyncOpenAccessGetLatestEvmAssociations(OpenAccessEndpointTest):
    endpoint = EndpointUnstable.LATEST_EVM_ASSOCIATIONS
    route_params = {"netuid": 1}
    http_method = HTTPMethod.GET

    def make_endpoint_call(self, client):
        return client.unstable.open_access.get_latest_evm_associations(netuid=NetUid(1))

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

    def test_success_with_no_evm_associations(self, pylon_client, service_mock, route_mock, block):
        self._setup_login_mock(service_mock)
        response_data = GetLatestEvmAssociationsResponse(block=block, evm_associations={})
        route_mock.mock(return_value=Response(status_code=codes.OK, json=response_data.model_dump(mode="json")))

        with pylon_client:
            response = pylon_client.unstable.open_access.get_latest_evm_associations(netuid=NetUid(1))

        assert response == response_data
