"""
Tests for the GET /subnet/{netuid}/block/{block_number}/validators endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient

from tests.world import VALIDATORS_NETUID


@pytest.mark.asyncio
async def test_v1_open_access_get_validators_returns_only_validator_permit_neurons_sorted_by_total_stake_desc(
    open_access_test_client: AsyncTestClient, snapshot_json
):
    response = await open_access_test_client.get(f"/api/v1/subnet/{VALIDATORS_NETUID}/block/321/validators")

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_v1_open_access_get_latest_validators_returns_only_validator_permit_neurons_sorted_by_total_stake_desc(
    open_access_test_client: AsyncTestClient, snapshot_json
):
    response = await open_access_test_client.get(f"/api/v1/subnet/{VALIDATORS_NETUID}/block/latest/validators")

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_get_validators_open_access_block_not_found(
    open_access_test_client: AsyncTestClient,
    mock_bt_client_factory,
    snapshot_json,
):
    async with mock_bt_client_factory() as mock_client:
        async with mock_client.mock_behavior(
            get_block=[None],
        ):
            response = await open_access_test_client.get("/api/v1/subnet/1/block/999999/validators")

            assert response.status_code == HTTP_404_NOT_FOUND
            assert response.json() == snapshot_json


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
    open_access_test_client: AsyncTestClient, invalid_block_number: str, snapshot_json
):
    response = await open_access_test_client.get(f"/api/v1/subnet/1/block/{invalid_block_number}/validators")

    assert response.status_code == HTTP_404_NOT_FOUND, response.content
    assert response.json() == snapshot_json
