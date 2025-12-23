from http import HTTPMethod

import pytest
from httpx import Response, codes
from pydantic import ValidationError

from pylon_client._internal.common.endpoints import Endpoint
from pylon_client._internal.common.models import Block
from pylon_client._internal.common.requests import GetNeuronsRequest
from pylon_client._internal.common.responses import GetNeuronsResponse
from pylon_client._internal.common.types import BlockHash, BlockNumber, NetUid
from tests.client.asynchronous.base_test import OpenAccessEndpointTest
from tests.factories import NeuronFactory


class TestOpenAccessGetNeurons(OpenAccessEndpointTest):
    endpoint = Endpoint.NEURONS
    route_params = {"netuid": 1, "block_number": 1000}
    http_method = HTTPMethod.GET

    async def make_endpoint_call(self, client):
        return await client.open_access.get_neurons(netuid=NetUid(1), block_number=BlockNumber(1000))

    @pytest.fixture
    def block(self) -> Block:
        return Block(number=BlockNumber(1000), hash=BlockHash("0x123"))

    @pytest.fixture
    def success_response(self, block: Block, neuron_factory: NeuronFactory) -> GetNeuronsResponse:
        neurons = neuron_factory.batch(2)
        return GetNeuronsResponse(block=block, neurons={neuron.hotkey: neuron for neuron in neurons})

    @pytest.mark.asyncio
    async def test_empty_neurons(self, pylon_client, service_mock, route_mock, block: Block):
        """
        Test getting neurons with no neurons returns empty dict.
        """
        expected_response = GetNeuronsResponse(block=block, neurons={})
        route_mock.mock(return_value=Response(status_code=codes.OK, json=expected_response.model_dump(mode="json")))

        async with pylon_client:
            response = await self.make_endpoint_call(pylon_client)

        assert response == expected_response


@pytest.mark.parametrize(
    "invalid_block_number,expected_errors",
    [
        pytest.param(
            "not_a_number",
            [
                {
                    "type": "int_parsing",
                    "loc": ("block_number",),
                    "msg": "Input should be a valid integer, unable to parse string as an integer",
                },
            ],
            id="string_value",
        ),
        pytest.param(
            123.456,
            [
                {
                    "type": "int_from_float",
                    "loc": ("block_number",),
                    "msg": "Input should be a valid integer, got a number with a fractional part",
                },
            ],
            id="float_value",
        ),
        pytest.param(
            [123],
            [
                {"type": "int_type", "loc": ("block_number",), "msg": "Input should be a valid integer"},
            ],
            id="list_value",
        ),
        pytest.param(
            {"block": 123},
            [
                {"type": "int_type", "loc": ("block_number",), "msg": "Input should be a valid integer"},
            ],
            id="dict_value",
        ),
    ],
)
def test_get_neurons_request_validation_error(invalid_block_number, expected_errors):
    """
    Test that GetNeuronsRequest validates block_number type correctly.
    """
    with pytest.raises(ValidationError) as exc_info:
        GetNeuronsRequest(netuid=NetUid(1), block_number=invalid_block_number)

    errors = exc_info.value.errors(include_url=False, include_context=False, include_input=False)
    assert errors == expected_errors
