from http import HTTPMethod

import pytest

from pylon_client._internal.pylon_commons.endpoints import Endpoint
from pylon_client._internal.pylon_commons.models import Block
from pylon_client._internal.pylon_commons.responses import GetNeuronsResponse
from pylon_client._internal.pylon_commons.types import BlockHash, BlockNumber, NetUid
from tests.factories import NeuronFactory
from tests.synchronous.base_test import OpenAccessEndpointTest


class TestSyncOpenAccessGetLatestNeurons(OpenAccessEndpointTest):
    endpoint = Endpoint.LATEST_NEURONS
    route_params = {"netuid": 1}
    http_method = HTTPMethod.GET

    def make_endpoint_call(self, client):
        return client.open_access.get_latest_neurons(netuid=NetUid(1))

    @pytest.fixture
    def block(self) -> Block:
        return Block(number=BlockNumber(1000), hash=BlockHash("0x123"))

    @pytest.fixture
    def success_response(self, block: Block, neuron_factory: NeuronFactory) -> GetNeuronsResponse:
        neurons = neuron_factory.batch(2)
        return GetNeuronsResponse(block=block, neurons={neuron.hotkey: neuron for neuron in neurons})
