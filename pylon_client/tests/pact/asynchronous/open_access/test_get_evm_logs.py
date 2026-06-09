import pytest
from httpx import codes
from pact import Pact

from pylon_client._internal.pylon_commons.types import evm as evm_types
from tests.pact.builders import build_empty_evm_logs_response, build_evm_logs_response
from tests.pact.constants import EVM_CONTRACT_ADDRESS, EVM_FROM_BLOCK, EVM_TO_BLOCK, EVM_TRANSFER_ABI, OPEN_ACCESS_TOKEN


@pytest.mark.asyncio
async def test_get_evm_logs_returns_logs(pact: Pact, get_evm_logs_response_matcher: dict, pylon_client_factory):
    (
        pact.upon_receiving("a request for evm contract logs")
        .given("evm contract logs exist", contract_address=EVM_CONTRACT_ADDRESS)
        .with_request("POST", f"/api/_unstable/openaccess/evm/contracts/{EVM_CONTRACT_ADDRESS}/logs")
        .with_header("Authorization", f"Bearer {OPEN_ACCESS_TOKEN}")
        .with_query_parameters({"from_block": str(EVM_FROM_BLOCK), "to_block": str(EVM_TO_BLOCK)})
        .with_body({"abi": EVM_TRANSFER_ABI}, content_type="application/json")
        .will_respond_with(codes.OK)
        .with_body(get_evm_logs_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url))
        async with client:
            response = await client.unstable.open_access.get_evm_logs(
                contract_address=evm_types.Address(EVM_CONTRACT_ADDRESS),
                from_block=evm_types.BlockNumber(EVM_FROM_BLOCK),
                to_block=evm_types.BlockNumber(EVM_TO_BLOCK),
                abi=EVM_TRANSFER_ABI,
            )

    assert response == build_evm_logs_response()


@pytest.mark.asyncio
async def test_get_evm_logs_returns_empty_logs(
    pact: Pact, get_evm_empty_logs_response_matcher: dict, pylon_client_factory
):
    (
        pact.upon_receiving("a request for evm contract logs with no results")
        .given("no evm contract logs exist", contract_address=EVM_CONTRACT_ADDRESS)
        .with_request("POST", f"/api/_unstable/openaccess/evm/contracts/{EVM_CONTRACT_ADDRESS}/logs")
        .with_header("Authorization", f"Bearer {OPEN_ACCESS_TOKEN}")
        .with_query_parameters({"from_block": str(EVM_FROM_BLOCK), "to_block": str(EVM_TO_BLOCK)})
        .with_body({"abi": EVM_TRANSFER_ABI}, content_type="application/json")
        .will_respond_with(codes.OK)
        .with_body(get_evm_empty_logs_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url))
        async with client:
            response = await client.unstable.open_access.get_evm_logs(
                contract_address=evm_types.Address(EVM_CONTRACT_ADDRESS),
                from_block=evm_types.BlockNumber(EVM_FROM_BLOCK),
                to_block=evm_types.BlockNumber(EVM_TO_BLOCK),
                abi=EVM_TRANSFER_ABI,
            )

    assert response == build_empty_evm_logs_response()
