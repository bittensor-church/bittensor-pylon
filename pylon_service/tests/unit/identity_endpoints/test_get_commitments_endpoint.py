import pytest
from litestar.status_codes import HTTP_200_OK

from tests.world import COMMITMENTS_ALL_NETUID, COMMITMENTS_EMPTY_NETUID, COMMITMENTS_FILTERED_NETUID


@pytest.mark.asyncio
async def test_v1_identity_get_commitments_returns_registered_commitments_as_hex_map(
    identity_test_client_factory, snapshot_json
):
    async with identity_test_client_factory("sn21") as client:
        response = await client.get(
            f"/api/v1/identity/sn21/subnet/{COMMITMENTS_ALL_NETUID}/block/latest/commitments",
        )

        assert response.status_code == HTTP_200_OK
        assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_v1_identity_get_commitments_filters_unregistered_commitments_and_keeps_valid_items(
    identity_test_client_factory, snapshot_json
):
    async with identity_test_client_factory("sn22") as client:
        response = await client.get(
            f"/api/v1/identity/sn22/subnet/{COMMITMENTS_FILTERED_NETUID}/block/latest/commitments",
        )

        assert response.status_code == HTTP_200_OK
        assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_v1_identity_get_commitments_returns_empty_map_when_none_exist(
    identity_test_client_factory, snapshot_json
):
    async with identity_test_client_factory("sn23") as client:
        response = await client.get(
            f"/api/v1/identity/sn23/subnet/{COMMITMENTS_EMPTY_NETUID}/block/latest/commitments",
        )

        assert response.status_code == HTTP_200_OK
        assert response.json() == snapshot_json
