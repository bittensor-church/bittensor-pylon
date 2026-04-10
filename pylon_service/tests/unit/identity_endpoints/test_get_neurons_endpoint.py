"""
Tests for the GET /identity/{identity_name}/subnet/{netuid}/block/{block_number}/neurons endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND


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
    identity_test_client_factory, invalid_block_number: str, snapshot_json
):
    """
    Test that invalid block number types return 404.
    """
    async with identity_test_client_factory("sn1") as client:
        response = await client.get(
            f"/api/v1/identity/sn1/subnet/1/block/{invalid_block_number}/neurons",
        )

        assert response.status_code == HTTP_404_NOT_FOUND, response.content
        assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_v1_identity_get_neurons_returns_block_neurons(identity_test_client_factory, snapshot_json):
    async with identity_test_client_factory("sn1") as client:
        response = await client.get("/api/v1/identity/sn1/subnet/1/block/123/neurons")

        assert response.status_code == HTTP_200_OK
        assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_v1_identity_get_latest_neurons_returns_latest_neurons(identity_test_client_factory, snapshot_json):
    async with identity_test_client_factory("sn1") as client:
        response = await client.get("/api/v1/identity/sn1/subnet/1/block/latest/neurons")

        assert response.status_code == HTTP_200_OK
        assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_get_neurons_identity_block_not_found(
    identity_test_client_factory, mock_bt_client_factory, snapshot_json
):
    """
    Test that non-existent block returns 404.
    """
    async with mock_bt_client_factory("sn1") as mock_client:
        async with mock_client.mock_behavior(get_block=[None]):
            async with identity_test_client_factory("sn1") as client:
                response = await client.get("/api/v1/identity/sn1/subnet/1/block/123/neurons")

                assert response.status_code == HTTP_404_NOT_FOUND, response.content
                assert response.json() == snapshot_json

        assert mock_client.calls["get_block"] == [(123,)]


@pytest.mark.asyncio
async def test_v1_identity_any_identity_scoped_endpoint_unknown_identity_returns_404(
    identity_test_client_factory, snapshot_json
):
    async with identity_test_client_factory("sn1") as client:
        response = await client.get("/api/v1/identity/unknown/subnet/1/block/latest/neurons")

        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.json() == snapshot_json
