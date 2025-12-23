from http import HTTPMethod

import pytest

from pylon_client._internal.common.endpoints import Endpoint
from pylon_client._internal.common.models import Block
from pylon_client._internal.common.responses import GetNeuronsResponse
from pylon_client._internal.common.types import BlockHash, BlockNumber
from tests.client.synchronous.base_test import IdentityEndpointTest
from tests.factories import NeuronFactory


class TestSyncIdentityGetLatestNeurons(IdentityEndpointTest):
    endpoint = Endpoint.LATEST_NEURONS
    route_params = {"identity_name": "sn1", "netuid": 1}
    http_method = HTTPMethod.GET

    def make_endpoint_call(self, client):
        return client.identity.get_latest_neurons()

    @pytest.fixture
    def block(self) -> Block:
        return Block(number=BlockNumber(1000), hash=BlockHash("0x123"))

    @pytest.fixture
    def success_response(self, block: Block, neuron_factory: NeuronFactory) -> GetNeuronsResponse:
        neurons = neuron_factory.batch(2)
        return GetNeuronsResponse(block=block, neurons={neuron.hotkey: neuron for neuron in neurons})
