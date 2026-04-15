import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient
from pylon_commons.models import Block
from pylon_commons.types import BlockHash, BlockNumber

from pylon_service.bittensor.contact import MockBittensorContact
from tests.world import OWN_COMMITMENT_NETUID, OWN_TIMELOCK_COMMITMENT_NETUID


@pytest.mark.asyncio
async def test_unstable_identity_get_own_commitment_returns_commitment_object(
    test_client: AsyncTestClient, snapshot_json
):
    response = await test_client.get(
        f"/api/_unstable/identity/sn2/subnet/{OWN_COMMITMENT_NETUID}/block/latest/commitments/self"
    )

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_unstable_identity_get_own_commitment_returns_timelock_variant(
    test_client: AsyncTestClient, snapshot_json
):
    response = await test_client.get(
        f"/api/_unstable/identity/sn2/subnet/{OWN_TIMELOCK_COMMITMENT_NETUID}/block/latest/commitments/self"
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
        response = await test_client.get("/api/_unstable/identity/sn2/subnet/2/block/latest/commitments/self")

    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_unstable_identity_get_own_commitment_unknown_identity_returns_404(test_client, snapshot_json):
    response = await test_client.get("/api/_unstable/identity/unknown/subnet/1/block/latest/commitments/self")

    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json() == snapshot_json
