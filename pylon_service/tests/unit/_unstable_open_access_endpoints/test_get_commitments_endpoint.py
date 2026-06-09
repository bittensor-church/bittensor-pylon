import pytest
from litestar.status_codes import HTTP_200_OK

from tests.world import (
    COMMITMENTS_ALL_NETUID,
    COMMITMENTS_EMPTY_NETUID,
    COMMITMENTS_FILTERED_NETUID,
    COMMITMENTS_MIXED_NETUID,
)


@pytest.mark.asyncio
async def test_unstable_open_access_get_commitments_returns_all_registered_commitments(
    open_access_test_client, snapshot_json
):
    response = await open_access_test_client.get(
        f"/api/_unstable/openaccess/subnet/{COMMITMENTS_ALL_NETUID}/block/latest/commitments"
    )

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_unstable_open_access_get_commitments_filters_unregistered_commitments_and_keeps_valid_items(
    open_access_test_client, snapshot_json
):
    response = await open_access_test_client.get(
        f"/api/_unstable/openaccess/subnet/{COMMITMENTS_FILTERED_NETUID}/block/latest/commitments"
    )

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_unstable_open_access_get_commitments_returns_empty_map_when_none_exist(
    open_access_test_client, snapshot_json
):
    response = await open_access_test_client.get(
        f"/api/_unstable/openaccess/subnet/{COMMITMENTS_EMPTY_NETUID}/block/latest/commitments"
    )

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_unstable_open_access_get_commitments_includes_timelock_variants(open_access_test_client, snapshot_json):
    response = await open_access_test_client.get(
        f"/api/_unstable/openaccess/subnet/{COMMITMENTS_MIXED_NETUID}/block/latest/commitments"
    )

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json
