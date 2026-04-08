import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND

from pylon_service.bittensor.contact import MockBittensorContact
from tests.world import VALIDATORS_NETUID


@pytest.mark.asyncio
async def test_v1_identity_get_validators_returns_only_validator_permit_neurons_sorted_by_total_stake_desc(
    test_client, snapshot_json
):
    response = await test_client.get(f"/api/v1/identity/val/subnet/{VALIDATORS_NETUID}/block/321/validators")

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_v1_identity_get_latest_validators_returns_only_validator_permit_neurons_sorted_by_total_stake_desc(
    test_client, snapshot_json
):
    response = await test_client.get(f"/api/v1/identity/val/subnet/{VALIDATORS_NETUID}/block/latest/validators")

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_v1_identity_get_validators_missing_block_returns_404(
    test_client, sn1_mock_bt_client: MockBittensorContact, snapshot_json
):
    async with sn1_mock_bt_client.mock_behavior(get_block=[None]):
        response = await test_client.get("/api/v1/identity/sn1/subnet/1/block/999999/validators")

    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json() == snapshot_json
