"""
Tests for the GET /subnet/{netuid}/block/latest/commitments/{hotkey} endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient
from pylon_commons.models import Block, Commitment
from pylon_commons.types import BlockHash, BlockNumber, Hotkey

from tests.mock_bittensor_client import MockBittensorClient


@pytest.mark.asyncio
async def test_unstable_open_access_get_commitment_by_hotkey_returns_commitment_object(
    test_client: AsyncTestClient, open_access_mock_bt_client: MockBittensorClient, snapshot_json
):
    block = Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))
    commitment = Commitment(
        commitment_block_number=BlockNumber(999),
        hotkey=Hotkey("hotkey1"),
        commitment="0x01020304",
    )

    async with open_access_mock_bt_client.mock_behavior(
        get_latest_block=[block],
        get_commitment=[commitment],
    ):
        response = await test_client.get("/api/_unstable/subnet/1/block/latest/commitments/hotkey1")

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_get_commitment_open_access_not_found(
    test_client: AsyncTestClient, open_access_mock_bt_client: MockBittensorClient, snapshot_json
):
    """
    Test getting a commitment that doesn't exist.
    """
    async with open_access_mock_bt_client.mock_behavior(
        get_latest_block=[Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))],
        get_commitment=[None],
    ):
        response = await test_client.get("/api/_unstable/subnet/1/block/latest/commitments/hotkey1")
    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json() == snapshot_json
