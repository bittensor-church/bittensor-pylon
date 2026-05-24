from http import HTTPMethod

import pytest
from httpx import Response, codes
from tenacity import wait_none

from pylon_client._internal.pylon_commons._unstable.endpoints import Endpoint as EndpointUnstable
from pylon_client.artanis import (
    ASYNC_DEFAULT_RETRIES,
    AsyncConfig,
    AsyncPylonClient,
    BlockHash,
    BlockNumber,
    NetUid,
    PylonAuthToken,
)
from pylon_client.artanis.unstable import Block, GetNeuronsResponse
from tests.factories import NeuronFactory
from tests.neurons_file_helpers import write_neurons_file
from tests.unit.asynchronous.base_test import OpenAccessEndpointTest


class TestOpenAccessGetLatestNeurons(OpenAccessEndpointTest):
    endpoint = EndpointUnstable.LATEST_NEURONS
    route_params = {"netuid": 1}
    http_method = HTTPMethod.GET

    async def make_endpoint_call(self, client):
        return await client.unstable.open_access.get_latest_neurons(netuid=NetUid(1))

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
        Test getting latest neurons with no neurons returns empty dict.
        """
        expected_response = GetNeuronsResponse(block=block, neurons={})
        route_mock.mock(return_value=Response(status_code=codes.OK, json=expected_response.model_dump(mode="json")))

        async with pylon_client:
            response = await self.make_endpoint_call(pylon_client)

        assert response == expected_response


@pytest.mark.asyncio
async def test_neurons_file_returns_file_backed_neurons(tmp_path, test_url):
    """
    Test that get_latest_neurons reads from file when neurons_file is configured.
    """
    neurons_file = tmp_path / "neurons.yaml"
    expected = write_neurons_file(
        neurons_file, {"5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY": ("127.0.0.1", 9090)}
    )
    client = AsyncPylonClient(
        AsyncConfig(
            address=test_url,
            open_access_token=PylonAuthToken("open_access_token"),
            neurons_file=str(neurons_file),
            retry=ASYNC_DEFAULT_RETRIES.copy(wait=wait_none()),
        )
    )
    async with client:
        response = await client.unstable.open_access.get_latest_neurons(netuid=NetUid(1))
    assert response == expected
