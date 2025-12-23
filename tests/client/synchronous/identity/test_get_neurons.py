from http import HTTPMethod

import pytest
from httpx import Response, codes

from pylon_client._internal.common.endpoints import Endpoint
from pylon_client._internal.common.models import Block
from pylon_client._internal.common.responses import GetNeuronsResponse
from pylon_client._internal.common.types import BlockHash, BlockNumber
from tests.client.synchronous.base_test import IdentityEndpointTest
from tests.factories import NeuronFactory


class TestSyncIdentityGetNeurons(IdentityEndpointTest):
    endpoint = Endpoint.NEURONS
    route_params = {"identity_name": "sn1", "netuid": 1, "block_number": 1000}
    http_method = HTTPMethod.GET

    def make_endpoint_call(self, client):
        return client.identity.get_neurons(block_number=BlockNumber(1000))

    def get_endpoint_response(self) -> Response:
        return Response(status_code=codes.OK, json={"block": {"number": 1000, "hash": "0x123"}, "neurons": {}})

    @pytest.fixture
    def block(self) -> Block:
        return Block(number=BlockNumber(1000), hash=BlockHash("0x123"))

    @pytest.fixture
    def success_response(self, block: Block, neuron_factory: NeuronFactory) -> GetNeuronsResponse:
        neurons = neuron_factory.batch(2)
        return GetNeuronsResponse(block=block, neurons={neuron.hotkey: neuron for neuron in neurons})

    def test_empty_neurons(self, pylon_client, service_mock, route_mock, block: Block):
        """
        Test getting neurons with no neurons returns empty dict.
        """
        self._setup_login_mock(service_mock)

        expected_response = GetNeuronsResponse(block=block, neurons={})
        route_mock.mock(return_value=Response(status_code=codes.OK, json=expected_response.model_dump(mode="json")))

        with pylon_client:
            response = self.make_endpoint_call(pylon_client)

        assert response == expected_response
