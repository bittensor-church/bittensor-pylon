"""
Tests for the GET /block/{block_number}/extrinsic/{extrinsic_index} endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient

from pylon_client._internal.common.models import Extrinsic, ExtrinsicCall
from pylon_client._internal.common.types import BlockNumber, ExtrinsicIndex
from tests.mock_bittensor_client import MockBittensorClient


@pytest.fixture
def sample_extrinsic() -> Extrinsic:
    """
    Sample extrinsic for testing.
    """
    return Extrinsic(
        block_number=BlockNumber(1000),
        extrinsic_index=ExtrinsicIndex(0),
        extrinsic_hash="0xabc123",
        extrinsic_length=100,
        address="5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
        call=ExtrinsicCall(
            call_module="Balances",
            call_function="transfer",
            call_args=[
                {"name": "dest", "type": "AccountId", "value": "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"},
                {"name": "value", "type": "Balance", "value": 1000000000},
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
        extrinsic_hash="0xf28cf21731dbe93b0fbb607334be06ec456f02c102084e08f19cc4d65b9b8434",
        extrinsic_length=10,
        address=None,
        call=ExtrinsicCall(
            call_module="Timestamp",
            call_function="set",
            call_args=[{"name": "now", "type": "Moment", "value": 1764090180000}],
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
    async with open_access_mock_bt_client.mock_behavior(
        get_extrinsic=[sample_extrinsic],
    ):
        response = await test_client.get("/api/v1/block/1000/extrinsic/0")

        assert response.status_code == HTTP_200_OK, response.content
        assert response.json() == sample_extrinsic.model_dump(mode="json")

    assert open_access_mock_bt_client.calls["get_extrinsic"] == [
        (BlockNumber(1000), ExtrinsicIndex(0)),
    ]


@pytest.mark.asyncio
async def test_get_extrinsic_unsigned_extrinsic(
    test_client: AsyncTestClient,
    open_access_mock_bt_client: MockBittensorClient,
    timestamp_extrinsic: Extrinsic,
):
    """
    Test getting an unsigned extrinsic (address is None).
    """
    async with open_access_mock_bt_client.mock_behavior(
        get_extrinsic=[timestamp_extrinsic],
    ):
        response = await test_client.get("/api/v1/block/1/extrinsic/0")

        assert response.status_code == HTTP_200_OK, response.content
        response_data = response.json()
        assert response_data["address"] is None
        assert response_data["call"]["call_module"] == "Timestamp"


@pytest.mark.asyncio
async def test_get_extrinsic_not_found(
    test_client: AsyncTestClient,
    open_access_mock_bt_client: MockBittensorClient,
):
    """
    Test that non-existent extrinsic returns 404.
    """
    async with open_access_mock_bt_client.mock_behavior(
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
        get_extrinsic=[None],
    ):
        response = await test_client.get("/api/v1/block/999999999/extrinsic/0")

        assert response.status_code == HTTP_404_NOT_FOUND, response.content
        assert response.json() == {
            "status_code": HTTP_404_NOT_FOUND,
            "detail": "Extrinsic 999999999-0 not found.",
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
    extrinsic_0 = Extrinsic(
        block_number=BlockNumber(100),
        extrinsic_index=ExtrinsicIndex(0),
        extrinsic_hash="0xhash0",
        extrinsic_length=10,
        address=None,
        call=ExtrinsicCall(call_module="Timestamp", call_function="set", call_args=[]),
    )
    extrinsic_1 = Extrinsic(
        block_number=BlockNumber(100),
        extrinsic_index=ExtrinsicIndex(1),
        extrinsic_hash="0xhash1",
        extrinsic_length=200,
        address="5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
        call=ExtrinsicCall(call_module="Balances", call_function="transfer", call_args=[]),
    )

    async with open_access_mock_bt_client.mock_behavior(
        get_extrinsic=[extrinsic_0, extrinsic_1],
    ):
        response_0 = await test_client.get("/api/v1/block/100/extrinsic/0")
        response_1 = await test_client.get("/api/v1/block/100/extrinsic/1")

        assert response_0.status_code == HTTP_200_OK
        assert response_0.json()["extrinsic_index"] == 0
        assert response_0.json()["call"]["call_module"] == "Timestamp"

        assert response_1.status_code == HTTP_200_OK
        assert response_1.json()["extrinsic_index"] == 1
        assert response_1.json()["call"]["call_module"] == "Balances"
