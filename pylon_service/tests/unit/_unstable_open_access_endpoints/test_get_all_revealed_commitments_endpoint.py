import pytest
from litestar.status_codes import HTTP_200_OK
from litestar.testing import AsyncTestClient

from tests.world import REVEALED_COMMITMENTS_NETUID


@pytest.mark.asyncio
async def test_unstable_open_access_get_all_revealed_commitments_returns_registered_lists(
    test_client: AsyncTestClient, snapshot_json
):
    response = await test_client.get(
        f"/api/_unstable/subnet/{REVEALED_COMMITMENTS_NETUID}/block/latest/commitments/revealed"
    )

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json
