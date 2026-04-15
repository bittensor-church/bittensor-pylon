import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient
from pylon_commons.models import Block
from pylon_commons.types import BlockHash, BlockNumber

from pylon_service.bittensor.contact import MockBittensorContact
from tests.world import REVEALED_COMMITMENTS_NETUID


@pytest.mark.asyncio
async def test_unstable_open_access_get_revealed_commitments_by_hotkey_returns_list(
    test_client: AsyncTestClient, snapshot_json
):
    response = await test_client.get(
        f"/api/_unstable/subnet/{REVEALED_COMMITMENTS_NETUID}/block/latest/commitments/revealed/hotkey1"
    )

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_unstable_open_access_get_revealed_commitments_by_hotkey_returns_404_when_missing(
    test_client: AsyncTestClient, open_access_mock_bt_client: MockBittensorContact, snapshot_json
):
    async with open_access_mock_bt_client.mock_behavior(
        get_latest_block=[Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))],
        get_revealed_commitments=[None],
    ):
        response = await test_client.get(
            f"/api/_unstable/subnet/{REVEALED_COMMITMENTS_NETUID}/block/latest/commitments/revealed/hotkey1"
        )

    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json() == snapshot_json
