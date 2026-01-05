import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient

from pylon_client._internal.common.models import Block, Commitment
from pylon_client._internal.common.types import BlockHash, BlockNumber, CommitmentDataHex, Hotkey
from tests.mock_bittensor_client import MockBittensorClient


@pytest.mark.asyncio
async def test_get_own_commitment_identity_success(
    test_client: AsyncTestClient, sn1_mock_bt_client: MockBittensorClient
):
    latest_block = Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))
    commitment = Commitment(
        block=latest_block,
        hotkey=Hotkey("5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"),
        commitment=CommitmentDataHex("0x0102030405060708"),
    )

    async with sn1_mock_bt_client.mock_behavior(
        get_latest_block=[latest_block],
        get_commitment=[commitment],
    ):
        response = await test_client.get("/api/v1/identity/sn1/subnet/1/block/latest/commitments/self")

    assert response.status_code == HTTP_200_OK
    assert response.json() == {
        "block": {"number": 1000, "hash": "0xabc123"},
        "hotkey": "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
        "commitment": "0x0102030405060708",
    }
    assert sn1_mock_bt_client.calls["get_commitment"] == [(1, latest_block, None)]


@pytest.mark.asyncio
async def test_get_own_commitment_identity_not_found(
    test_client: AsyncTestClient, sn2_mock_bt_client: MockBittensorClient
):
    latest_block = Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))

    async with sn2_mock_bt_client.mock_behavior(
        get_latest_block=[latest_block],
        get_commitment=[None],
    ):
        response = await test_client.get("/api/v1/identity/sn2/subnet/2/block/latest/commitments/self")

    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json() == {
        "detail": "Commitment not found.",
        "status_code": HTTP_404_NOT_FOUND,
    }
