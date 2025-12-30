from http import HTTPMethod

import pytest
from httpx import Response, codes

from pylon_client._internal.common.endpoints import Endpoint
from pylon_client._internal.common.models import Block
from pylon_client._internal.common.responses import GetValidatorsResponse
from pylon_client._internal.common.types import BlockHash, BlockNumber, NetUid
from tests.client.asynchronous.base_test import OpenAccessEndpointTest
from tests.factories import NeuronFactory


class TestOpenAccessGetValidators(OpenAccessEndpointTest):
    endpoint = Endpoint.VALIDATORS
    route_params = {"netuid": 1, "block_number": 1000}
    http_method = HTTPMethod.GET

    async def make_endpoint_call(self, client):
        return await client.open_access.get_validators(netuid=NetUid(1), block_number=BlockNumber(1000))

    @pytest.fixture
    def block(self) -> Block:
        return Block(number=BlockNumber(1000), hash=BlockHash("0x123"))

    @pytest.fixture
    def success_response(self, block: Block, neuron_factory: NeuronFactory) -> GetValidatorsResponse:
        validators = neuron_factory.batch(2)
        return GetValidatorsResponse(block=block, validators=validators)

    @pytest.mark.asyncio
    async def test_empty_validators(self, pylon_client, service_mock, route_mock, block: Block):
        expected_response = GetValidatorsResponse(block=block, validators=[])
        route_mock.mock(return_value=Response(status_code=codes.OK, json=expected_response.model_dump(mode="json")))

        async with pylon_client:
            response = await self.make_endpoint_call(pylon_client)

        assert response == expected_response
