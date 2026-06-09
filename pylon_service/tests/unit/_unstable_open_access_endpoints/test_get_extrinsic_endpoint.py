import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from pylon_commons.models import Block, Extrinsic, ExtrinsicCall
from pylon_commons.types import BlockHash, BlockNumber, ExtrinsicHash, ExtrinsicIndex, ExtrinsicLength


@pytest.mark.asyncio
async def test_unstable_open_access_get_extrinsic_missing_extrinsic_returns_404(
    open_access_test_client,
    mock_bt_client_factory,
    snapshot_json,
):
    block = Block(number=BlockNumber(999), hash=BlockHash("0xblock999"))

    async with mock_bt_client_factory() as mock_client:
        async with mock_client.mock_behavior(
            get_block=[block],
            get_extrinsic=[None],
        ):
            response = await open_access_test_client.get("/api/_unstable/openaccess/block/999/extrinsic/99")

    assert response.status_code == HTTP_404_NOT_FOUND, response.content
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_unstable_open_access_get_extrinsic_missing_block_returns_404(
    open_access_test_client,
    mock_bt_client_factory,
    snapshot_json,
):
    async with mock_bt_client_factory() as mock_client:
        async with mock_client.mock_behavior(get_block=[None]):
            response = await open_access_test_client.get("/api/_unstable/openaccess/block/999999999/extrinsic/0")

    assert response.status_code == HTTP_404_NOT_FOUND, response.content
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_unstable_open_access_get_extrinsic_returns_decoded_extrinsic(
    open_access_test_client,
    mock_bt_client_factory,
    snapshot_json,
):
    block = Block(number=BlockNumber(100), hash=BlockHash("0xblock100"))
    extrinsic = Extrinsic(
        block_number=BlockNumber(100),
        extrinsic_index=ExtrinsicIndex(1),
        extrinsic_hash=ExtrinsicHash("0xhash1"),
        extrinsic_length=ExtrinsicLength(200),
        address="5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
        call=ExtrinsicCall(call_module="Balances", call_function="transfer", call_args=[]),
    )

    async with mock_bt_client_factory() as mock_client:
        async with mock_client.mock_behavior(
            get_block=[block],
            get_extrinsic=[extrinsic],
        ):
            response = await open_access_test_client.get("/api/_unstable/openaccess/block/100/extrinsic/1")

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json
