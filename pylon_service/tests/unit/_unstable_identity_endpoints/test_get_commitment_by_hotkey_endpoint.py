"""
Tests for the GET identity/{id}/subnet/{netuid}/block/latest/commitments/{hotkey} endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from pylon_commons.models import Block
from pylon_commons.types import BlockHash, BlockNumber

from tests.world import COMMITMENTS_ALL_NETUID


@pytest.mark.asyncio
async def test_unstable_identity_get_commitment_by_hotkey_returns_commitment_object(
    identity_test_client_factory, snapshot_json
):
    async with identity_test_client_factory("sn21") as client:
        response = await client.get(
            f"/api/_unstable/identity/sn21/subnet/{COMMITMENTS_ALL_NETUID}/block/latest/commitments/hotkey1",
        )

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_get_commitment_identity_not_found(identity_test_client_factory, mock_bt_client_factory, snapshot_json):
    """
    Test getting a commitment that doesn't exist.
    """
    async with mock_bt_client_factory("sn1") as mock_client:
        async with mock_client.mock_behavior(
            get_latest_block=[Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))],
            get_commitment=[None],
        ):
            async with identity_test_client_factory("sn1") as client:
                response = await client.get(
                    "/api/_unstable/identity/sn1/subnet/1/block/latest/commitments/hotkey1",
                )
    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json() == snapshot_json
