"""
Tests for the GET /subnet/{netuid}/block/{block_number}/validators endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient
from pylon_commons.models import Block
from pylon_commons.types import BlockNumber, NetUid

from pylon_service.bittensor.client import MockTurboBTtransport


@pytest.mark.asyncio
async def test_get_validators_open_access_success(
    test_client: AsyncTestClient,
    mock_turbobt_transport: MockTurboBTtransport,
    default_netuid: NetUid,
    default_block: Block,
):
    response = await test_client.get(f"/api/v1/subnet/{int(default_netuid)}/block/{default_block.number}/validators")

    assert response.status_code == HTTP_200_OK
    assert response.json() == {
        "block": {"number": 123, "hash": "0xabc123"},
        "validators": [
            {
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
        ],
    }

    assert mock_turbobt_transport.calls["get_block"] == [(default_block.number,), (BlockNumber(-1),)]
    assert mock_turbobt_transport.calls["list_neurons"] == [(default_netuid, default_block.hash)]
    assert mock_turbobt_transport.calls["get_subnet_state"] == [(default_netuid, default_block.hash)]


@pytest.mark.asyncio
async def test_get_latest_validators_open_access_success(
    test_client: AsyncTestClient,
    mock_turbobt_transport: MockTurboBTtransport,
    default_netuid: NetUid,
    default_block: Block,
):
    response = await test_client.get(f"/api/v1/subnet/{int(default_netuid)}/block/latest/validators")

    assert response.status_code == HTTP_200_OK
    assert response.json() == {
        "block": {"number": 123, "hash": "0xabc123"},
        "validators": [
            {
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
        ],
    }

    assert mock_turbobt_transport.calls["get_block"] == [(BlockNumber(-1),), (BlockNumber(-1),)]
    assert mock_turbobt_transport.calls["list_neurons"] == [(default_netuid, default_block.hash)]
    assert mock_turbobt_transport.calls["get_subnet_state"] == [(default_netuid, default_block.hash)]


@pytest.mark.asyncio
async def test_get_validators_open_access_block_not_found(
    test_client: AsyncTestClient,
    mock_turbobt_transport: MockTurboBTtransport,
    default_netuid: NetUid,
):
    response = await test_client.get(f"/api/v1/subnet/{int(default_netuid)}/block/999999/validators")

    assert response.status_code == HTTP_404_NOT_FOUND, response.content
    assert response.json() == {
        "status_code": HTTP_404_NOT_FOUND,
        "detail": "Block 999999 not found.",
    }

    assert mock_turbobt_transport.calls["get_block"] == [(BlockNumber(999999),)]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_block_number",
    [
        pytest.param("not_a_number", id="string_value"),
        pytest.param("123.456", id="float_string"),
        pytest.param("true", id="boolean_string"),
    ],
)
async def test_get_validators_open_access_invalid_block_number_type(
    test_client: AsyncTestClient,
    default_netuid: NetUid,
    invalid_block_number: str,
):
    response = await test_client.get(f"/api/v1/subnet/{int(default_netuid)}/block/{invalid_block_number}/validators")

    assert response.status_code == HTTP_404_NOT_FOUND, response.content
    assert response.json() == {"status_code": HTTP_404_NOT_FOUND, "detail": "Not Found"}
