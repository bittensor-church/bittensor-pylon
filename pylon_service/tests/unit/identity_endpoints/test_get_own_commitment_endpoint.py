import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient
from pylon_commons.models import Block
from pylon_commons.types import BlockHash, BlockNumber

from pylon_service.bittensor.mock_contact import MockBittensorContact
from tests.world import OWN_COMMITMENT_NETUID, OWN_TIMELOCK_COMMITMENT_NETUID


@pytest.mark.asyncio
async def test_v1_identity_get_own_commitment_returns_v1_commitment_shape(test_client: AsyncTestClient, snapshot_json):
    response = await test_client.get(
        f"/api/v1/identity/sn2/subnet/{OWN_COMMITMENT_NETUID}/block/latest/commitments/self"
    )

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_get_own_commitment_identity_not_found(
    test_client: AsyncTestClient, sn2_mock_bt_client: MockBittensorContact, snapshot_json
):
    latest_block = Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))

    async with sn2_mock_bt_client.mock_behavior(
        get_latest_block=[latest_block],
        get_commitment=[None],
    ):
        response = await test_client.get("/api/v1/identity/sn2/subnet/2/block/latest/commitments/self")

    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_v1_identity_get_own_commitment_unknown_identity_returns_404(test_client, snapshot_json):
    response = await test_client.get("/api/v1/identity/unknown/subnet/1/block/latest/commitments/self")

    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_v1_identity_get_own_commitment_returns_404_for_timelock_commitment(
    test_client: AsyncTestClient, snapshot_json
):
    response = await test_client.get(
        f"/api/v1/identity/sn2/subnet/{OWN_TIMELOCK_COMMITMENT_NETUID}/block/latest/commitments/self"
    )

    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json() == snapshot_json
