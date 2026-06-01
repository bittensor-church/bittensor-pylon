import pytest
from litestar.status_codes import HTTP_200_OK

from tests.world import (
    EVM_ASSOCIATIONS_NETUID,
    NO_EVM_ASSOCIATIONS_NETUID,
)


@pytest.mark.asyncio
async def test_unstable_identity_get_latest_evm_associations_returns_data(identity_test_client_factory, snapshot_json):
    async with identity_test_client_factory("sn29") as client:
        response = await client.get(
            f"/api/_unstable/identity/sn29/subnet/{EVM_ASSOCIATIONS_NETUID}/block/latest/evm_associations",
        )

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_unstable_identity_get_latest_evm_associations_returns_empty_map_when_none_exist(
    identity_test_client_factory, snapshot_json
):
    async with identity_test_client_factory("sn30") as client:
        response = await client.get(
            f"/api/_unstable/identity/sn30/subnet/{NO_EVM_ASSOCIATIONS_NETUID}/block/latest/evm_associations",
        )

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json
