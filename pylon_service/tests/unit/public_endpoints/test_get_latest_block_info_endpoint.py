import pytest
from litestar.status_codes import HTTP_200_OK
from pylon_commons.models import Block
from pylon_commons.types import BlockHash, BlockNumber, Timestamp

from pylon_service.bittensor.exceptions import BittensorTransportError
from pylon_service.bittensor.mock_contact import MockBittensorContact


@pytest.mark.asyncio
async def test_v1_public_latest_block_info_returns_latest_block_info(
    test_client, mock_bt_client_factory, snapshot_json
):
    block = Block(number=BlockNumber(123), hash=BlockHash("0xabc123"))

    async with mock_bt_client_factory() as mock_client:
        async with mock_client.mock_behavior(
            get_latest_block=[block],
            get_block_timestamp=[Timestamp(1_700_000_000)],
        ):
            response = await test_client.get("/api/v1/block/latest")

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_v1_public_latest_block_info_returns_502_for_contact_transport_error(test_client, mock_bt_client_factory):
    async with mock_bt_client_factory() as mock_client:
        async with mock_client.mock_behavior(
            get_latest_block=[
                BittensorTransportError(
                    operation="get_latest_block",
                    uri="mock://main",
                    original_exception=RuntimeError("subtensor unavailable"),
                )
            ]
        ):
            response = await test_client.get("/api/v1/block/latest")

    assert response.status_code == 502
    assert response.json() == {
        "status_code": 502,
        "detail": "get_latest_block failed on mock://main: RuntimeError: subtensor unavailable",
    }
