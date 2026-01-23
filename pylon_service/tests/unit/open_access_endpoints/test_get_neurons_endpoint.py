"""
Tests for the GET /subnet/{netuid}/block/{block_number}/neurons endpoint.
"""

import pytest
from litestar.status_codes import HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient

from tests.mock_bittensor_client import MockBittensorClient


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_block_number",
    [
        pytest.param("not_a_number", id="string_value"),
        pytest.param("123.456", id="float_string"),
        pytest.param("true", id="boolean_string"),
    ],
)
async def test_get_neurons_open_access_invalid_block_number_type(
    test_client: AsyncTestClient, invalid_block_number: str
):
    """
    Test that invalid block number types return 404.
    """
    response = await test_client.get(f"/api/v1/subnet/1/block/{invalid_block_number}/neurons")

    assert response.status_code == HTTP_404_NOT_FOUND, response.content
    assert response.json() == {
        "status_code": HTTP_404_NOT_FOUND,
        "detail": "Not Found",
    }


@pytest.mark.asyncio
async def test_get_neurons_open_access_block_not_found(
    test_client: AsyncTestClient, open_access_mock_bt_client: MockBittensorClient
):
    """
    Test that non-existent block returns 404.
    """
    async with open_access_mock_bt_client.mock_behavior(get_block=[None]):
        response = await test_client.get("/api/v1/subnet/1/block/123/neurons")

        assert response.status_code == HTTP_404_NOT_FOUND, response.content
        assert response.json() == {
            "status_code": HTTP_404_NOT_FOUND,
            "detail": "Block 123 not found.",
        }

    assert open_access_mock_bt_client.calls["get_block"] == [(123,)]
