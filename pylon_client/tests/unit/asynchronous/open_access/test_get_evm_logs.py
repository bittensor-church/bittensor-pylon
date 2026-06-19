from http import HTTPMethod
from typing import Any

import pytest
from httpx import Response, codes

from pylon_client._internal.pylon_commons._unstable.endpoints import Endpoint as EndpointUnstable
from pylon_client._internal.pylon_commons.types import evm as evm_types
from pylon_client.artanis.unstable import EvmLog, GetEvmLogsResponse
from tests.unit.asynchronous.base_test import OpenAccessEndpointTest

_CONTRACT_ADDRESS = evm_types.Address("0x000000000000000000000000000000000000dead")
_FROM_BLOCK = evm_types.BlockNumber(100)
_TO_BLOCK = evm_types.BlockNumber(200)
_ABI: list[dict[str, Any]] = [
    {
        "type": "event",
        "name": "Transfer",
        "anonymous": False,
        "inputs": [
            {"name": "from", "type": "address", "indexed": True},
            {"name": "to", "type": "address", "indexed": True},
            {"name": "value", "type": "uint256", "indexed": False},
        ],
    }
]


class TestAsyncOpenAccessGetEvmLogs(OpenAccessEndpointTest):
    endpoint = EndpointUnstable.EVM_LOGS
    route_params = {"contract_address": _CONTRACT_ADDRESS}
    http_method = HTTPMethod.POST

    async def make_endpoint_call(self, client):
        return await client.unstable.open_access.get_evm_logs(
            contract_address=_CONTRACT_ADDRESS,
            from_block=_FROM_BLOCK,
            to_block=_TO_BLOCK,
            abi=_ABI,
        )

    @pytest.fixture
    def success_response(self) -> GetEvmLogsResponse:
        return GetEvmLogsResponse(
            logs=[
                EvmLog(
                    event="Transfer",
                    args={"from": "0xaaaa", "to": "0xbbbb", "value": 1000},
                    address=evm_types.Address("0x000000000000000000000000000000000000dead"),
                    block_number=evm_types.BlockNumber(150),
                    transaction_hash=evm_types.TransactionHash("0xdeadbeef"),
                    transaction_index=evm_types.TransactionIndex(0),
                    log_index=evm_types.LogIndex(0),
                )
            ],
            from_block=_FROM_BLOCK,
            to_block=_TO_BLOCK,
        )

    @pytest.mark.asyncio
    async def test_success_with_empty_logs(self, pylon_client, service_mock, route_mock):
        self._setup_login_mock(service_mock)
        response_data = GetEvmLogsResponse(logs=[], from_block=_FROM_BLOCK, to_block=_TO_BLOCK)
        route_mock.mock(return_value=Response(status_code=codes.OK, json=response_data.model_dump(mode="json")))

        async with pylon_client:
            response = await pylon_client.unstable.open_access.get_evm_logs(
                contract_address=_CONTRACT_ADDRESS,
                from_block=_FROM_BLOCK,
                to_block=_TO_BLOCK,
                abi=_ABI,
            )

        assert response == response_data
