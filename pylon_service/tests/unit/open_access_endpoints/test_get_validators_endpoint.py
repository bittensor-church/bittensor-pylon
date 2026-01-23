"""
Tests for the GET /subnet/{netuid}/block/{block_number}/validators endpoint.
"""

import pytest
from litestar.status_codes import HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient

from tests.mock_bittensor_client import MockBittensorClient


@pytest.mark.asyncio
async def test_get_validators_open_access_block_not_found(
    test_client: AsyncTestClient,
    open_access_mock_bt_client: MockBittensorClient,
):
    async with open_access_mock_bt_client.mock_behavior(
        get_block=[None],
    ):
        response = await test_client.get("/api/v1/subnet/1/block/999999/validators")

        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "Block 999999 not found.", "status_code": 404}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_block_number",
    [
        pytest.param("not_a_number", id="string_value"),
        pytest.param("123.456", id="float_string"),
        pytest.param("true", id="boolean_string"),
    ],
)
async def test_get_validators_open_access_invalid_block_number_type(
    test_client: AsyncTestClient, invalid_block_number: str
):
    response = await test_client.get(f"/api/v1/subnet/1/block/{invalid_block_number}/validators")

    assert response.status_code == HTTP_404_NOT_FOUND, response.content
    assert response.json() == {"status_code": HTTP_404_NOT_FOUND, "detail": "Not Found"}
