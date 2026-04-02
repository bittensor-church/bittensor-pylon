"""
Tests for the GET /subnet/{netuid}/block/{block_number}/neurons endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient
from pylon_commons.models import Block
from pylon_commons.types import BlockNumber, NetUid

from pylon_service.bittensor.client import MockTurboBTtransport


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_block_number",
    [
        pytest.param("not_a_number", id="string_value"),
        pytest.param("123.456", id="float_string"),
        pytest.param("true", id="boolean_string"),
    ],
)
async def test_get_neurons_open_access_invalid_block_number_type(
    test_client: AsyncTestClient,
    default_netuid: NetUid,
    invalid_block_number: str,
):
    response = await test_client.get(f"/api/v1/subnet/{int(default_netuid)}/block/{invalid_block_number}/neurons")

    assert response.status_code == HTTP_404_NOT_FOUND, response.content
    assert response.json() == {
        "status_code": HTTP_404_NOT_FOUND,
        "detail": "Not Found",
    }


@pytest.mark.asyncio
async def test_get_neurons_open_access_success(
    test_client: AsyncTestClient,
    mock_turbobt_transport: MockTurboBTtransport,
    default_netuid: NetUid,
    default_block: Block,
):
    response = await test_client.get(f"/api/v1/subnet/{int(default_netuid)}/block/{default_block.number}/neurons")

    assert response.status_code == HTTP_200_OK, response.content
    assert response.json() == {
        "block": {"number": 123, "hash": "0xabc123"},
        "neurons": {
            "hotkey-a": {
                "uid": 10,
                "coldkey": "coldkey-a",
                "hotkey": "hotkey-a",
                "active": True,
                "axon_info": {"ip": "192.168.1.10", "port": 8080, "protocol": 4},
                "stake": 1.5,
                "rank": 0.11,
                "emission": 2.5,
                "incentive": 0.22,
                "consensus": 0.33,
                "trust": 0.44,
                "validator_trust": 0.55,
                "dividends": 0.66,
                "last_update": 111,
                "validator_permit": True,
                "pruning_score": 7,
                "stakes": {"alpha": 3.5, "tao": 4.5, "total": 8.0},
            },
            "hotkey-b": {
                "uid": 11,
                "coldkey": "coldkey-b",
                "hotkey": "hotkey-b",
                "active": False,
                "axon_info": {"ip": "10.0.0.2", "port": 9090, "protocol": 0},
                "stake": 9.5,
                "rank": 0.77,
                "emission": 1.25,
                "incentive": 0.88,
                "consensus": 0.99,
                "trust": 0.12,
                "validator_trust": 0.34,
                "dividends": 0.56,
                "last_update": 222,
                "validator_permit": False,
                "pruning_score": 8,
                "stakes": {"alpha": 5.5, "tao": 6.5, "total": 12.0},
            },
        },
    }

    assert mock_turbobt_transport.calls["get_block"] == [(default_block.number,), (BlockNumber(-1),)]
    assert mock_turbobt_transport.calls["list_neurons"] == [(default_netuid, default_block.hash)]
    assert mock_turbobt_transport.calls["get_subnet_state"] == [(default_netuid, default_block.hash)]


@pytest.mark.asyncio
async def test_get_latest_neurons_open_access_success(
    test_client: AsyncTestClient,
    mock_turbobt_transport: MockTurboBTtransport,
    default_netuid: NetUid,
    default_block: Block,
):
    response = await test_client.get(f"/api/v1/subnet/{int(default_netuid)}/block/latest/neurons")

    assert response.status_code == HTTP_200_OK, response.content
    assert response.json() == {
        "block": {"number": 123, "hash": "0xabc123"},
        "neurons": {
            "hotkey-a": {
                "uid": 10,
                "coldkey": "coldkey-a",
                "hotkey": "hotkey-a",
                "active": True,
                "axon_info": {"ip": "192.168.1.10", "port": 8080, "protocol": 4},
                "stake": 1.5,
                "rank": 0.11,
                "emission": 2.5,
                "incentive": 0.22,
                "consensus": 0.33,
                "trust": 0.44,
                "validator_trust": 0.55,
                "dividends": 0.66,
                "last_update": 111,
                "validator_permit": True,
                "pruning_score": 7,
                "stakes": {"alpha": 3.5, "tao": 4.5, "total": 8.0},
            },
            "hotkey-b": {
                "uid": 11,
                "coldkey": "coldkey-b",
                "hotkey": "hotkey-b",
                "active": False,
                "axon_info": {"ip": "10.0.0.2", "port": 9090, "protocol": 0},
                "stake": 9.5,
                "rank": 0.77,
                "emission": 1.25,
                "incentive": 0.88,
                "consensus": 0.99,
                "trust": 0.12,
                "validator_trust": 0.34,
                "dividends": 0.56,
                "last_update": 222,
                "validator_permit": False,
                "pruning_score": 8,
                "stakes": {"alpha": 5.5, "tao": 6.5, "total": 12.0},
            },
        },
    }

    assert mock_turbobt_transport.calls["get_block"] == [(BlockNumber(-1),), (BlockNumber(-1),)]
    assert mock_turbobt_transport.calls["list_neurons"] == [(default_netuid, default_block.hash)]
    assert mock_turbobt_transport.calls["get_subnet_state"] == [(default_netuid, default_block.hash)]


@pytest.mark.asyncio
async def test_get_neurons_open_access_block_not_found(
    test_client: AsyncTestClient,
    mock_turbobt_transport: MockTurboBTtransport,
    default_netuid: NetUid,
):
    response = await test_client.get(f"/api/v1/subnet/{int(default_netuid)}/block/999999/neurons")

    assert response.status_code == HTTP_404_NOT_FOUND, response.content
    assert response.json() == {
        "status_code": HTTP_404_NOT_FOUND,
        "detail": "Block 999999 not found.",
    }

    assert mock_turbobt_transport.calls["get_block"] == [(BlockNumber(999999),)]
