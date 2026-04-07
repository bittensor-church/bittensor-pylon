import pytest
from litestar.status_codes import HTTP_200_OK
from tests.world import COMMITMENTS_ALL_NETUID, COMMITMENTS_EMPTY_NETUID, COMMITMENTS_FILTERED_NETUID


@pytest.mark.asyncio
async def test_v1_open_access_get_commitments_returns_registered_commitments_as_hex_map(
    test_client, snapshot_json
):
    response = await test_client.get(f"/api/v1/subnet/{COMMITMENTS_ALL_NETUID}/block/latest/commitments")

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_v1_open_access_get_commitments_filters_unregistered_commitments_and_keeps_valid_items(
    test_client, snapshot_json
):
    response = await test_client.get(f"/api/v1/subnet/{COMMITMENTS_FILTERED_NETUID}/block/latest/commitments")

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_v1_open_access_get_commitments_returns_empty_map_when_none_exist(
    test_client, snapshot_json
):
    response = await test_client.get(f"/api/v1/subnet/{COMMITMENTS_EMPTY_NETUID}/block/latest/commitments")

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json
