"""
Tests for the GET /subnet/{netuid}/block/{block_number}/validators endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient

from pylon_client._internal.common.models import Block, Neuron, SubnetValidators
from pylon_client._internal.common.types import ValidatorPermit
from tests.factories import BlockFactory, NeuronFactory
from tests.mock_bittensor_client import MockBittensorClient


@pytest.fixture
def block(block_factory: BlockFactory) -> Block:
    return block_factory.build()


@pytest.fixture
def validators(neuron_factory: NeuronFactory) -> list[Neuron]:
    validator1 = neuron_factory.build(validator_permit=ValidatorPermit(True), stakes={"total": 300.0})
    validator2 = neuron_factory.build(validator_permit=ValidatorPermit(True), stakes={"total": 200.0})
    validator3 = neuron_factory.build(validator_permit=ValidatorPermit(True), stakes={"total": 100.0})
    return [validator1, validator2, validator3]


@pytest.fixture
def subnet_validators(validators: list[Neuron], block: Block) -> SubnetValidators:
    return SubnetValidators(block=block, validators=validators)


@pytest.mark.asyncio
async def test_get_validators_open_access_success(
    test_client: AsyncTestClient,
    open_access_mock_bt_client: MockBittensorClient,
    subnet_validators: SubnetValidators,
    block: Block,
):
    async with open_access_mock_bt_client.mock_behavior(
        get_block=[block],
        get_validators=[subnet_validators],
    ):
        response = await test_client.get("/api/v1/subnet/1/block/1000/validators")

        assert response.status_code == HTTP_200_OK, response.content
        assert response.json() == subnet_validators.model_dump(mode="json")

    assert open_access_mock_bt_client.calls["get_block"] == [(1000,)]
    assert open_access_mock_bt_client.calls["get_validators"] == [(1, block)]


@pytest.mark.asyncio
async def test_get_validators_open_access_empty_list(
    test_client: AsyncTestClient,
    open_access_mock_bt_client: MockBittensorClient,
    block: Block,
):
    empty_validators = SubnetValidators(block=block, validators=[])

    async with open_access_mock_bt_client.mock_behavior(
        get_block=[block],
        get_validators=[empty_validators],
    ):
        response = await test_client.get("/api/v1/subnet/1/block/100/validators")

        assert response.status_code == HTTP_200_OK, response.content
        assert response.json() == empty_validators.model_dump(mode="json")


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
