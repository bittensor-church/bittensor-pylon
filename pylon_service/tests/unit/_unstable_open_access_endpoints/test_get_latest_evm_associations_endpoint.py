import pytest
from litestar.status_codes import HTTP_200_OK

from tests.world import (
    EVM_ASSOCIATIONS_NETUID,
    NO_EVM_ASSOCIATIONS_NETUID,
)


@pytest.mark.asyncio
async def test_unstable_open_access_get_latest_evm_associations_returns_data(open_access_test_client, snapshot_json):
    response = await open_access_test_client.get(
        f"/api/_unstable/openaccess/subnet/{EVM_ASSOCIATIONS_NETUID}/block/latest/evm_associations",
    )

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_unstable_open_access_get_latest_evm_associations_returns_empty_map_when_none_exist(
    open_access_test_client, snapshot_json
):
    response = await open_access_test_client.get(
        f"/api/_unstable/openaccess/subnet/{NO_EVM_ASSOCIATIONS_NETUID}/block/latest/evm_associations",
    )

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json
