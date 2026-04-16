import pytest
from litestar.status_codes import HTTP_200_OK
from pylon_commons.models import Block
from pylon_commons.types import BlockHash, BlockNumber, Timestamp

from pylon_service.bittensor.mock_contact import MockBittensorContact


@pytest.mark.asyncio
async def test_unstable_public_latest_block_info_returns_latest_block_info(
    test_client, open_access_mock_bt_client: MockBittensorContact, snapshot_json
):
    block = Block(number=BlockNumber(123), hash=BlockHash("0xabc123"))

    async with open_access_mock_bt_client.mock_behavior(
        get_latest_block=[block],
        get_block_timestamp=[Timestamp(1_700_000_000)],
    ):
        response = await test_client.get("/api/_unstable/block/latest")

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json
