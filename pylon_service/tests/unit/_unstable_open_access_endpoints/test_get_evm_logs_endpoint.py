import pytest
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_502_BAD_GATEWAY,
)
from litestar.testing import AsyncTestClient
from pylon_commons.models import EvmLog
from pylon_commons.types import evm as evm_types

from pylon_service.evm.exceptions import EvmInvalidAbiError, EvmInvalidAddressError, EvmRpcError

_CONTRACT_ADDRESS = "0x1234567890123456789012345678901234567890"
_ABI = [{"type": "event", "name": "Transfer", "inputs": []}]
_URL = f"/api/_unstable/openaccess/evm/contracts/{_CONTRACT_ADDRESS}/logs"
_PARAMS = {"from_block": 100, "to_block": 200}


def _log(event="Transfer", block_number=150):
    return EvmLog(
        event=event,
        args={"from": "0xabc", "to": "0xdef", "value": 1000},
        address=evm_types.Address(_CONTRACT_ADDRESS),
        block_number=evm_types.BlockNumber(block_number),
        transaction_hash=evm_types.TransactionHash("0xdeadbeef"),
        transaction_index=evm_types.TransactionIndex(0),
        log_index=evm_types.LogIndex(0),
    )


@pytest.mark.asyncio
async def test_unstable_open_access_evm_logs_returns_logs(
    open_access_test_client: AsyncTestClient, mock_evm_client, snapshot_json
):
    """
    Test that a successful request returns decoded EVM logs.
    """
    logs = [_log("Transfer", 150), _log("Transfer", 160)]
    async with mock_evm_client.mock_behavior(get_current_block=1000, get_logs=lambda *_, **__: logs):
        response = await open_access_test_client.post(_URL, params=_PARAMS, json={"abi": _ABI})

    assert response.status_code == HTTP_200_OK
    assert snapshot_json == response.json()


@pytest.mark.asyncio
async def test_unstable_open_access_evm_logs_returns_empty_list_when_no_logs(
    open_access_test_client: AsyncTestClient, mock_evm_client, snapshot_json
):
    """
    Test that a request with no matching logs returns an empty list.
    """
    async with mock_evm_client.mock_behavior(get_current_block=1000, get_logs=lambda *_, **__: []):
        response = await open_access_test_client.post(_URL, params=_PARAMS, json={"abi": _ABI})

    assert response.status_code == HTTP_200_OK
    assert snapshot_json == response.json()


@pytest.mark.asyncio
async def test_unstable_open_access_evm_logs_invalid_address_returns_400(
    open_access_test_client: AsyncTestClient, mock_evm_client, snapshot_json
):
    """
    Test that an invalid contract address returns 400.
    """
    async with mock_evm_client.mock_behavior(
        get_current_block=1000,
        get_logs=EvmInvalidAddressError("Invalid contract address: not_an_address"),
    ):
        response = await open_access_test_client.post(
            "/api/_unstable/openaccess/evm/contracts/not_an_address/logs",
            params=_PARAMS,
            json={"abi": _ABI},
        )

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert snapshot_json == response.json()


@pytest.mark.asyncio
async def test_unstable_open_access_evm_logs_malformed_abi_returns_422(
    open_access_test_client: AsyncTestClient, mock_evm_client, snapshot_json
):
    """
    Test that a malformed event ABI entry (missing name) returns 422.
    """
    async with mock_evm_client.mock_behavior(
        get_current_block=1000,
        get_logs=EvmInvalidAbiError("Malformed ABI event entry: 'name'"),
    ):
        response = await open_access_test_client.post(
            _URL, params=_PARAMS, json={"abi": [{"type": "event", "inputs": []}]}
        )

    assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY
    assert snapshot_json == response.json()


@pytest.mark.asyncio
async def test_unstable_open_access_evm_logs_function_only_abi_returns_empty_list(
    open_access_test_client: AsyncTestClient, mock_evm_client
):
    """
    Test that an ABI containing only function entries (no events) returns an empty list.
    """
    async with mock_evm_client.mock_behavior(
        get_current_block=1000,
        get_logs=lambda *_, **__: [],
    ):
        response = await open_access_test_client.post(_URL, params=_PARAMS, json={"abi": [{"type": "function"}]})

    assert response.status_code == HTTP_200_OK
    assert response.json() == {"logs": [], "from_block": 100, "to_block": 200}


@pytest.mark.asyncio
async def test_unstable_open_access_evm_logs_rpc_error_returns_502(
    open_access_test_client: AsyncTestClient, mock_evm_client, snapshot_json
):
    """
    Test that an EVM RPC node error returns 502.
    """
    async with mock_evm_client.mock_behavior(
        get_current_block=1000,
        get_logs=EvmRpcError("upstream RPC error"),
    ):
        response = await open_access_test_client.post(_URL, params=_PARAMS, json={"abi": _ABI})

    assert response.status_code == HTTP_502_BAD_GATEWAY
    assert snapshot_json == response.json()


@pytest.mark.asyncio
async def test_unstable_open_access_evm_logs_missing_abi_returns_400(
    open_access_test_client: AsyncTestClient,
):
    """
    Test that a request without an ABI body returns 400.
    """
    response = await open_access_test_client.post(_URL, params=_PARAMS, json={})

    assert response.status_code == HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_unstable_open_access_evm_logs_missing_token_returns_401(test_client: AsyncTestClient):
    """
    Test that the endpoint requires open access authentication.
    """
    response = await test_client.post(_URL, params=_PARAMS, json={"abi": _ABI})

    assert response.status_code == HTTP_401_UNAUTHORIZED
