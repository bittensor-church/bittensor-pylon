"""
Tests for the GET identity/{id}/subnet/{netuid}/block/latest/commitments/{hotkey} endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient
from pylon_commons.models import Block
from pylon_commons.types import BlockHash, BlockNumber

from pylon_service.bittensor.contact import MockBittensorContact
from tests.world import COMMITMENTS_ALL_NETUID


@pytest.mark.asyncio
async def test_v1_identity_get_commitment_by_hotkey_returns_v1_commitment_shape(
    test_client: AsyncTestClient, snapshot_json
):
    response = await test_client.get(
        f"/api/v1/identity/sn1/subnet/{COMMITMENTS_ALL_NETUID}/block/latest/commitments/hotkey1"
    )

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_get_commitment_identity_not_found(
    test_client: AsyncTestClient, sn1_mock_bt_client: MockBittensorContact, snapshot_json
):
    """
    Test getting a commitment that doesn't exist.
    """
    async with sn1_mock_bt_client.mock_behavior(
        get_latest_block=[Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))],
        get_commitment=[None],
    ):
        response = await test_client.get("/api/v1/identity/sn1/subnet/1/block/latest/commitments/hotkey1")
    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json() == snapshot_json
