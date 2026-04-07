"""
Tests for the GET /subnet/{netuid}/block/{block_number}/validators endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient
from pylon_commons.currency import Currency, Token
from pylon_commons.models import Block, Stakes, SubnetNeurons
from pylon_commons.types import BlockHash, BlockNumber, NetUid

from tests.factories import NeuronFactory
from tests.mock_bittensor_client import MockBittensorClient


def _build_validator_neurons(block: Block) -> SubnetNeurons:
    high = NeuronFactory.build(
        hotkey="validator-high",
        validator_permit=True,
        stakes=Stakes(alpha=Currency[Token.ALPHA](1), tao=Currency[Token.TAO](1), total=Currency[Token.ALPHA](9)),
    )
    low = NeuronFactory.build(
        hotkey="validator-low",
        validator_permit=True,
        stakes=Stakes(alpha=Currency[Token.ALPHA](1), tao=Currency[Token.TAO](1), total=Currency[Token.ALPHA](3)),
    )
    hidden = NeuronFactory.build(
        hotkey="non-validator",
        validator_permit=False,
        stakes=Stakes(alpha=Currency[Token.ALPHA](1), tao=Currency[Token.TAO](1), total=Currency[Token.ALPHA](99)),
    )
    return SubnetNeurons(block=block, neurons={n.hotkey: n for n in (low, hidden, high)})


@pytest.mark.asyncio
async def test_v1_open_access_get_validators_returns_only_validator_permit_neurons_sorted_by_total_stake_desc(
    test_client: AsyncTestClient,
    open_access_mock_bt_client: MockBittensorClient,
    snapshot_json,
):
    block = Block(number=BlockNumber(321), hash=BlockHash("0xblock321"))
    subnet_neurons = _build_validator_neurons(block)

    async with open_access_mock_bt_client.mock_behavior(
        get_block=[block],
        get_neurons=[subnet_neurons],
    ):
        response = await test_client.get("/api/v1/subnet/1/block/321/validators")

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_v1_open_access_get_latest_validators_returns_only_validator_permit_neurons_sorted_by_total_stake_desc(
    test_client: AsyncTestClient,
    open_access_mock_bt_client: MockBittensorClient,
    snapshot_json,
):
    block = Block(number=BlockNumber(654), hash=BlockHash("0xlatest654"))
    subnet_neurons = _build_validator_neurons(block)

    async with open_access_mock_bt_client.mock_behavior(
        get_latest_block=[block],
        get_neurons=[subnet_neurons],
    ):
        response = await test_client.get("/api/v1/subnet/1/block/latest/validators")

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_get_validators_open_access_block_not_found(
    test_client: AsyncTestClient,
    open_access_mock_bt_client: MockBittensorClient,
    snapshot_json,
):
    async with open_access_mock_bt_client.mock_behavior(
        get_block=[None],
    ):
        response = await test_client.get("/api/v1/subnet/1/block/999999/validators")

        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.json() == snapshot_json


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
    test_client: AsyncTestClient, invalid_block_number: str, snapshot_json
):
    response = await test_client.get(f"/api/v1/subnet/1/block/{invalid_block_number}/validators")

    assert response.status_code == HTTP_404_NOT_FOUND, response.content
    assert response.json() == snapshot_json
