from http import HTTPMethod

import pytest
from httpx import Response, codes
from tenacity import wait_none

from pylon_client._internal.pylon_commons._unstable.endpoints import Endpoint as EndpointUnstable
from pylon_client.artanis import (
    DEFAULT_RETRIES,
    BlockHash,
    BlockNumber,
    Config,
    IdentityName,
    PylonAuthToken,
    PylonClient,
    PylonResponseException,
)
from pylon_client.artanis.unstable import Block, GetNeuronsResponse
from tests.factories import NeuronFactory
from tests.neurons_file_helpers import write_neurons_file
from tests.unit.synchronous.base_test import IdentityEndpointTest


class TestSyncIdentityGetRecentNeurons(IdentityEndpointTest):
    endpoint = EndpointUnstable.RECENT_NEURONS
    route_params = {"identity_name": "sn1", "netuid": 1}
    http_method = HTTPMethod.GET

    def make_endpoint_call(self, client):
        return client.unstable.identity.get_recent_neurons()

    @pytest.fixture
    def block(self) -> Block:
        return Block(number=BlockNumber(1000), hash=BlockHash("0x123"))

    @pytest.fixture
    def success_response(self, block: Block, neuron_factory: NeuronFactory) -> GetNeuronsResponse:
        neurons = neuron_factory.batch(2)
        return GetNeuronsResponse(block=block, neurons={neuron.hotkey: neuron for neuron in neurons})

    def test_unavailable_response(self, pylon_client, service_mock, route_mock):
        self._setup_login_mock(service_mock)

        route_mock.mock(return_value=Response(status_code=codes.SERVICE_UNAVAILABLE))

        with pylon_client:
            with pytest.raises(PylonResponseException, match="Invalid response from Pylon API."):
                self.make_endpoint_call(pylon_client)


def test_neurons_file_returns_file_backed_neurons(tmp_path, test_url):
    """
    Test that get_recent_neurons reads from file when neurons_file is configured.
    """
    neurons_file = tmp_path / "neurons.yaml"
    expected = write_neurons_file(
        neurons_file, {"5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY": ("127.0.0.1", 9090)}
    )
    client = PylonClient(
        Config(
            address=test_url,
            identity_name=IdentityName("sn1"),
            identity_token=PylonAuthToken("sn1_token"),
            neurons_file=str(neurons_file),
            retry=DEFAULT_RETRIES.copy(wait=wait_none()),
        )
    )
    with client:
        response = client.unstable.identity.get_recent_neurons()
    assert response == expected
