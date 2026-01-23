"""
Tests for the GET /block/{block_number}/extrinsic/{extrinsic_index} endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient
from pylon_commons.models import Block, Extrinsic, ExtrinsicCall, ExtrinsicCallArg
from pylon_commons.types import BlockHash, BlockNumber, ExtrinsicHash, ExtrinsicIndex, ExtrinsicLength

from tests.mock_bittensor_client import MockBittensorClient


@pytest.fixture
def sample_extrinsic() -> Extrinsic:
    """
    Sample extrinsic for testing.
    """
    return Extrinsic(
        block_number=BlockNumber(1000),
        extrinsic_index=ExtrinsicIndex(0),
        extrinsic_hash=ExtrinsicHash("0xabc123"),
        extrinsic_length=ExtrinsicLength(100),
        address="5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
        call=ExtrinsicCall(
            call_module="Balances",
            call_function="transfer",
            call_args=[
                ExtrinsicCallArg(
                    name="dest", type="AccountId", value="5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"
                ),
                ExtrinsicCallArg(name="value", type="Balance", value=1_000_000_000),
            ],
        ),
    )


@pytest.fixture
def timestamp_extrinsic() -> Extrinsic:
    """
    Sample unsigned extrinsic (like timestamp.set).
    """
    return Extrinsic(
        block_number=BlockNumber(1),
        extrinsic_index=ExtrinsicIndex(0),
        extrinsic_hash=ExtrinsicHash("0xf28cf21731dbe93b0fbb607334be06ec456f02c102084e08f19cc4d65b9b8434"),
        extrinsic_length=ExtrinsicLength(10),
        address=None,
        call=ExtrinsicCall(
            call_module="Timestamp",
            call_function="set",
            call_args=[ExtrinsicCallArg(name="now", type="Moment", value=1_764_090_180_000)],
        ),
    )


@pytest.mark.asyncio
async def test_get_extrinsic_success(
    test_client: AsyncTestClient,
    open_access_mock_bt_client: MockBittensorClient,
    sample_extrinsic: Extrinsic,
):
    """
    Test getting an extrinsic successfully.
    """
    block = Block(number=BlockNumber(1000), hash=BlockHash("0xblock1000"))
    async with open_access_mock_bt_client.mock_behavior(
        get_block=[block],
        get_extrinsic=[sample_extrinsic],
    ):
        response = await test_client.get("/api/v1/block/1000/extrinsic/0")

        assert response.status_code == HTTP_200_OK, response.content
        assert response.json() == sample_extrinsic.model_dump(mode="json")

    assert open_access_mock_bt_client.calls["get_block"] == [(BlockNumber(1000),)]
    assert open_access_mock_bt_client.calls["get_extrinsic"] == [(block, ExtrinsicIndex(0))]


@pytest.mark.asyncio
async def test_get_extrinsic_unsigned_extrinsic(
    test_client: AsyncTestClient,
    open_access_mock_bt_client: MockBittensorClient,
    timestamp_extrinsic: Extrinsic,
):
    """
    Test getting an unsigned extrinsic (address is None).
    """
    block = Block(number=BlockNumber(1), hash=BlockHash("0xblock1"))
    async with open_access_mock_bt_client.mock_behavior(
        get_block=[block],
        get_extrinsic=[timestamp_extrinsic],
    ):
        response = await test_client.get("/api/v1/block/1/extrinsic/0")

        assert response.status_code == HTTP_200_OK, response.content
        assert response.json() == timestamp_extrinsic.model_dump(mode="json")


@pytest.mark.asyncio
async def test_get_extrinsic_not_found(
    test_client: AsyncTestClient,
    open_access_mock_bt_client: MockBittensorClient,
):
    """
    Test that non-existent extrinsic returns 404.
    """
    block = Block(number=BlockNumber(999), hash=BlockHash("0xblock999"))
    async with open_access_mock_bt_client.mock_behavior(
        get_block=[block],
        get_extrinsic=[None],
    ):
        response = await test_client.get("/api/v1/block/999/extrinsic/99")

        assert response.status_code == HTTP_404_NOT_FOUND, response.content
        assert response.json() == {
            "status_code": HTTP_404_NOT_FOUND,
            "detail": "Extrinsic 999-99 not found.",
        }


@pytest.mark.asyncio
async def test_get_extrinsic_block_not_found(
    test_client: AsyncTestClient,
    open_access_mock_bt_client: MockBittensorClient,
):
    """
    Test that non-existent block returns 404.
    """
    async with open_access_mock_bt_client.mock_behavior(
        get_block=[None],
    ):
        response = await test_client.get("/api/v1/block/999999999/extrinsic/0")

        assert response.status_code == HTTP_404_NOT_FOUND, response.content
        assert response.json() == {
            "status_code": HTTP_404_NOT_FOUND,
            "detail": "Block 999999999 not found.",
        }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_block_number",
    [
        pytest.param("not_a_number", id="string_value"),
        pytest.param("123.456", id="float_string"),
        pytest.param("true", id="boolean_string"),
    ],
)
async def test_get_extrinsic_invalid_block_number_type(
    test_client: AsyncTestClient,
    invalid_block_number: str,
):
    """
    Test that invalid block number types return 404.
    """
    response = await test_client.get(f"/api/v1/block/{invalid_block_number}/extrinsic/0")

    assert response.status_code == HTTP_404_NOT_FOUND, response.content
    assert response.json() == {
        "status_code": HTTP_404_NOT_FOUND,
        "detail": "Not Found",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_extrinsic_index",
    [
        pytest.param("not_a_number", id="string_value"),
        pytest.param("123.456", id="float_string"),
        pytest.param("true", id="boolean_string"),
    ],
)
async def test_get_extrinsic_invalid_extrinsic_index_type(
    test_client: AsyncTestClient,
    invalid_extrinsic_index: str,
):
    """
    Test that invalid extrinsic index types return 404.
    """
    response = await test_client.get(f"/api/v1/block/1000/extrinsic/{invalid_extrinsic_index}")

    assert response.status_code == HTTP_404_NOT_FOUND, response.content
    assert response.json() == {
        "status_code": HTTP_404_NOT_FOUND,
        "detail": "Not Found",
    }


@pytest.mark.asyncio
async def test_get_extrinsic_different_indices(
    test_client: AsyncTestClient,
    open_access_mock_bt_client: MockBittensorClient,
):
    """
    Test getting different extrinsics from the same block.
    """
    block = Block(number=BlockNumber(100), hash=BlockHash("0xblock100"))
    extrinsic_0 = Extrinsic(
        block_number=BlockNumber(100),
        extrinsic_index=ExtrinsicIndex(0),
        extrinsic_hash=ExtrinsicHash("0xhash0"),
        extrinsic_length=ExtrinsicLength(10),
        address=None,
        call=ExtrinsicCall(call_module="Timestamp", call_function="set", call_args=[]),
    )
    extrinsic_1 = Extrinsic(
        block_number=BlockNumber(100),
        extrinsic_index=ExtrinsicIndex(1),
        extrinsic_hash=ExtrinsicHash("0xhash1"),
        extrinsic_length=ExtrinsicLength(200),
        address="5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
        call=ExtrinsicCall(call_module="Balances", call_function="transfer", call_args=[]),
    )

    async with open_access_mock_bt_client.mock_behavior(
        get_block=[block, block],
        get_extrinsic=[extrinsic_0, extrinsic_1],
    ):
        response_0 = await test_client.get("/api/v1/block/100/extrinsic/0")
        response_1 = await test_client.get("/api/v1/block/100/extrinsic/1")

        assert response_0.status_code == HTTP_200_OK
        assert response_0.json() == extrinsic_0.model_dump(mode="json")

        assert response_1.status_code == HTTP_200_OK
        assert response_1.json() == extrinsic_1.model_dump(mode="json")
