import pytest
from litestar.status_codes import HTTP_200_OK
from pylon_commons.models import Block
from pylon_commons.types import BlockHash, BlockNumber, Timestamp


@pytest.mark.asyncio
async def test_unstable_open_access_latest_block_info_returns_latest_block_info(
    open_access_test_client, mock_bt_client_factory, snapshot_json
):
    block = Block(number=BlockNumber(123), hash=BlockHash("0xabc123"))

    async with mock_bt_client_factory() as mock_client:
        async with mock_client.mock_behavior(
            get_latest_block=[block],
            get_block_timestamp=[Timestamp(1_700_000_000)],
        ):
            response = await open_access_test_client.get("/api/_unstable/openaccess/block/latest")

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json
