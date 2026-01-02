from http import HTTPMethod

import pytest
from httpx import Response, codes

from pylon_client._internal.common.endpoints import Endpoint
from pylon_client._internal.common.exceptions import PylonResponseException
from pylon_client._internal.common.models import Block
from pylon_client._internal.common.responses import GetNeuronsResponse
from pylon_client._internal.common.types import BlockHash, BlockNumber
from tests.client.asynchronous.base_test import IdentityEndpointTest
from tests.factories import NeuronFactory


class TestIdentityGetRecentNeurons(IdentityEndpointTest):
    endpoint = Endpoint.RECENT_NEURONS
    route_params = {"identity_name": "sn1", "netuid": 1}
    http_method = HTTPMethod.GET

    async def make_endpoint_call(self, client):
        return await client.identity.get_recent_neurons()

    @pytest.fixture
    def block(self) -> Block:
        return Block(number=BlockNumber(1000), hash=BlockHash("0x123"))

    @pytest.fixture
    def success_response(self, block: Block, neuron_factory: NeuronFactory) -> GetNeuronsResponse:
        neurons = neuron_factory.batch(2)
        return GetNeuronsResponse(block=block, neurons={neuron.hotkey: neuron for neuron in neurons})

    @pytest.mark.asyncio
    async def test_unavailable_response(self, pylon_client, service_mock, route_mock):
        self._setup_login_mock(service_mock)

        route_mock.mock(return_value=Response(status_code=codes.SERVICE_UNAVAILABLE))

        async with pylon_client:
            with pytest.raises(PylonResponseException, match="Invalid response from Pylon API."):
                await self.make_endpoint_call(pylon_client)
