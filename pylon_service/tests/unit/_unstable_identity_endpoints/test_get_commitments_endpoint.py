import pytest
from litestar.status_codes import HTTP_200_OK

from tests.world import (
    COMMITMENTS_ALL_NETUID,
    COMMITMENTS_EMPTY_NETUID,
    COMMITMENTS_FILTERED_NETUID,
    COMMITMENTS_MIXED_NETUID,
)


@pytest.mark.asyncio
async def test_unstable_identity_get_commitments_returns_all_registered_commitments(
    identity_test_client_factory, snapshot_json
):
    async with identity_test_client_factory("sn21") as client:
        response = await client.get(
            f"/api/_unstable/identity/sn21/subnet/{COMMITMENTS_ALL_NETUID}/block/latest/commitments",
        )

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_unstable_identity_get_commitments_filters_unregistered_commitments_and_keeps_valid_items(
    identity_test_client_factory, snapshot_json
):
    async with identity_test_client_factory("sn22") as client:
        response = await client.get(
            f"/api/_unstable/identity/sn22/subnet/{COMMITMENTS_FILTERED_NETUID}/block/latest/commitments",
        )

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_unstable_identity_get_commitments_returns_empty_map_when_none_exist(
    identity_test_client_factory, snapshot_json
):
    async with identity_test_client_factory("sn23") as client:
        response = await client.get(
            f"/api/_unstable/identity/sn23/subnet/{COMMITMENTS_EMPTY_NETUID}/block/latest/commitments",
        )

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_unstable_identity_get_commitments_returns_hex_and_timelock_variants(test_client, snapshot_json):
    response = await test_client.get(
        f"/api/_unstable/identity/sn1/subnet/{COMMITMENTS_MIXED_NETUID}/block/latest/commitments"
    )

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json
