"""
Tests for the GET /identity/{identity_name}/subnet/{netuid}/block/{block_number}/neurons endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient

from pylon_service.bittensor.contact import MockBittensorContact


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_block_number",
    [
        pytest.param("not_a_number", id="string_value"),
        pytest.param("123.456", id="float_string"),
        pytest.param("true", id="boolean_string"),
    ],
)
async def test_get_neurons_identity_invalid_block_number_type(
    test_client: AsyncTestClient, invalid_block_number: str, snapshot_json
):
    """
    Test that invalid block number types return 404.
    """
    response = await test_client.get(f"/api/_unstable/identity/sn1/subnet/1/block/{invalid_block_number}/neurons")

    assert response.status_code == HTTP_404_NOT_FOUND, response.content
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_unstable_identity_get_neurons_returns_block_neurons(test_client: AsyncTestClient, snapshot_json):
    response = await test_client.get("/api/_unstable/identity/sn1/subnet/1/block/123/neurons")

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_unstable_identity_get_latest_neurons_returns_latest_neurons(test_client: AsyncTestClient, snapshot_json):
    response = await test_client.get("/api/_unstable/identity/sn1/subnet/1/block/latest/neurons")

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_get_neurons_identity_block_not_found(
    test_client: AsyncTestClient, sn1_mock_bt_client: MockBittensorContact, snapshot_json
):
    """
    Test that non-existent block returns 404.
    """
    async with sn1_mock_bt_client.mock_behavior(get_block=[None]):
        response = await test_client.get("/api/_unstable/identity/sn1/subnet/1/block/123/neurons")

        assert response.status_code == HTTP_404_NOT_FOUND, response.content
        assert response.json() == snapshot_json

    assert sn1_mock_bt_client.calls["get_block"] == [(123,)]


@pytest.mark.asyncio
async def test_unstable_identity_any_identity_scoped_endpoint_unknown_identity_returns_401(test_client):
    response = await test_client.get("/api/_unstable/identity/unknown/subnet/1/block/latest/neurons")

    assert response.status_code == HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated", "status_code": 401}
