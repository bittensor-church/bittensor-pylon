"""
Tests for the GET identity/{id}/subnet/{netuid}/block/latest/commitments endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK
from litestar.testing import AsyncTestClient

from pylon_client._internal.common.models import Block, SubnetCommitments
from pylon_client._internal.common.types import BlockHash, BlockNumber, CommitmentDataHex, Hotkey
from tests.mock_bittensor_client import MockBittensorClient


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "commitments",
    [
        pytest.param(
            {
                Hotkey("hotkey1"): CommitmentDataHex("0x01020304"),
                Hotkey("hotkey2"): CommitmentDataHex("0x05060708"),
            },
            id="multiple_commitments",
        ),
        pytest.param(
            {},
            id="empty_commitments",
        ),
    ],
)
async def test_get_commitments_identity(
    test_client: AsyncTestClient,
    sn1_mock_bt_client: MockBittensorClient,
    commitments: dict,
):
    """
    Test getting commitments from the subnet.
    """
    latest_block = Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))
    subnet_commitments = SubnetCommitments(block=latest_block, commitments=commitments)

    async with sn1_mock_bt_client.mock_behavior(
        get_latest_block=[latest_block],
        get_commitments=[subnet_commitments],
    ):
        response = await test_client.get("/api/v1/identity/sn1/subnet/1/block/latest/commitments")
    assert response.status_code == HTTP_200_OK
    assert response.json() == subnet_commitments.model_dump(mode="json")
