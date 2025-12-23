"""
Tests for the GET identity/{id}/subnet/{netuid}/block/latest/commitments/{hotkey} endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient

from pylon_client._internal.common.models import Block, Commitment
from pylon_client._internal.common.types import BlockHash, BlockNumber, CommitmentDataHex, Hotkey
from tests.mock_bittensor_client import MockBittensorClient


@pytest.mark.asyncio
async def test_get_commitment_identity_success(test_client: AsyncTestClient, sn1_mock_bt_client: MockBittensorClient):
    """
    Test getting a specific commitment successfully.
    """
    hotkey = "hotkey1"
    block = Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))
    commitment = Commitment(block=block, hotkey=Hotkey(hotkey), commitment=CommitmentDataHex("0x0102030405060708"))
    async with sn1_mock_bt_client.mock_behavior(
        get_latest_block=[block],
        get_commitment=[commitment],
    ):
        response = await test_client.get(f"/api/v1/identity/sn1/subnet/1/block/latest/commitments/{hotkey}")
    assert response.status_code == HTTP_200_OK
    assert response.json() == commitment.model_dump(mode="json")


@pytest.mark.asyncio
async def test_get_commitment_identity_not_found(test_client: AsyncTestClient, sn1_mock_bt_client: MockBittensorClient):
    """
    Test getting a commitment that doesn't exist.
    """
    async with sn1_mock_bt_client.mock_behavior(
        get_latest_block=[Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))],
        get_commitment=[None],
    ):
        response = await test_client.get("/api/v1/identity/sn1/subnet/1/block/latest/commitments/hotkey1")
    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json() == {
        "detail": "Commitment not found.",
        "status_code": HTTP_404_NOT_FOUND,
    }
