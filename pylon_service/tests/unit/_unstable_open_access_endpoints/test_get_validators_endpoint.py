"""
Tests for the GET /subnet/{netuid}/block/{block_number}/validators endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient

from pylon_service.bittensor.contact import MockBittensorContact
from tests.world import VALIDATORS_NETUID


@pytest.mark.asyncio
async def test_unstable_open_access_get_validators_returns_only_validator_permit_neurons_sorted_by_total_stake_desc(
    test_client: AsyncTestClient, snapshot_json
):
    response = await test_client.get(f"/api/_unstable/subnet/{VALIDATORS_NETUID}/block/321/validators")

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_unstable_open_access_get_latest_validators_returns_only_validator_permit_neurons_sorted_by_total_stake_desc(
    test_client: AsyncTestClient, snapshot_json
):
    response = await test_client.get(f"/api/_unstable/subnet/{VALIDATORS_NETUID}/block/latest/validators")

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_get_validators_open_access_block_not_found(
    test_client: AsyncTestClient,
    open_access_mock_bt_client: MockBittensorContact,
    snapshot_json,
):
    async with open_access_mock_bt_client.mock_behavior(
        get_block=[None],
    ):
        response = await test_client.get("/api/_unstable/subnet/1/block/999999/validators")

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
    test_client: AsyncTestClient, invalid_block_number: str, snapshot_json
):
    response = await test_client.get(f"/api/_unstable/subnet/1/block/{invalid_block_number}/validators")

    assert response.status_code == HTTP_404_NOT_FOUND, response.content
    assert response.json() == snapshot_json
