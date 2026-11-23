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
    MechanismId,
    NetUid,
    PylonAuthToken,
    PylonClient,
    PylonMechanismMismatch,
)
from pylon_client.artanis.unstable import Block, GetNeuronsResponse
from tests.factories import NeuronFactory
from tests.neurons_file_helpers import write_neurons_file
from tests.unit.synchronous.base_test import IdentityEndpointTest


class TestSyncIdentityGetLatestNeurons(IdentityEndpointTest):
    endpoint = EndpointUnstable.LATEST_NEURONS
    route_params = {"identity_name": "sn1", "netuid": 1}
    http_method = HTTPMethod.GET

    def make_endpoint_call(self, client):
        return client.unstable.identity.get_latest_neurons()

    @pytest.fixture
    def block(self) -> Block:
        return Block(number=BlockNumber(1000), hash=BlockHash("0x123"))

    @pytest.fixture
    def success_response(self, block: Block, neuron_factory: NeuronFactory) -> GetNeuronsResponse:
        neurons = neuron_factory.batch(2)
        return GetNeuronsResponse(block=block, neurons={neuron.hotkey: neuron for neuron in neurons})

    def test_mechanism_sends_query_and_checks_answer(self, service_mock, pylon_client, endpoint_url, success_response):
        """
        Test that a non-zero mechanism is sent as a query parameter and the matching answer is returned.
        """
        self._setup_login_mock(service_mock)
        body = success_response.model_copy(update={"mechanism_id": MechanismId(1)}).model_dump(mode="json")
        route = service_mock.get(endpoint_url, params={"mechanism_id": "1"}).mock(
            return_value=Response(status_code=codes.OK, json=body)
        )

        with pylon_client:
            response = pylon_client.unstable.identity.get_latest_neurons(mechanism_id=MechanismId(1))

        assert route.called
        assert response.mechanism_id == 1

    def test_mechanism_rejects_service_without_support(
        self, service_mock, pylon_client, endpoint_url, success_response
    ):
        """
        Test that an answer without the requested mechanism raises PylonMechanismMismatch.
        """
        self._setup_login_mock(service_mock)
        # A service without mechanism support ignores the query and answers without a mechanism_id field.
        body = success_response.model_dump(mode="json", exclude={"mechanism_id"})
        service_mock.get(endpoint_url, params={"mechanism_id": "1"}).mock(
            return_value=Response(status_code=codes.OK, json=body)
        )

        with pylon_client:
            with pytest.raises(PylonMechanismMismatch):
                pylon_client.unstable.identity.get_latest_neurons(mechanism_id=MechanismId(1))

    def test_default_mechanism_sends_no_query(self, service_mock, pylon_client, route_mock, success_response):
        """
        Test that the default mechanism sends no query string.
        """
        self._setup_login_mock(service_mock)
        route_mock.mock(return_value=Response(status_code=codes.OK, json=success_response.model_dump(mode="json")))

        with pylon_client:
            pylon_client.unstable.identity.get_latest_neurons()

        assert route_mock.calls.last.request.url.query == b""


def test_neurons_file_returns_file_backed_neurons(tmp_path, test_url):
    """
    Test that get_latest_neurons reads from file when neurons_file is configured.
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
        response = client.unstable.identity.get_latest_neurons()
    assert response == expected


def test_neurons_file_is_bypassed_for_other_mechanisms(tmp_path, test_url, service_mock):
    """
    Test that a configured neurons_file answers only mechanism 0; other mechanisms are read from the service.
    """
    neurons_file = tmp_path / "neurons.yaml"
    file_backed = write_neurons_file(
        neurons_file, {"5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY": ("127.0.0.1", 9090)}
    )
    service_mock.get(EndpointUnstable.IDENTITIES.absolute_url(is_public_=True)).mock(
        return_value=Response(status_code=codes.OK, json={"identities": {"sn1": 1}})
    )
    body = file_backed.model_copy(update={"mechanism_id": MechanismId(1)}).model_dump(mode="json")
    route = service_mock.get(
        EndpointUnstable.LATEST_NEURONS.absolute_url(netuid_=NetUid(1), identity_name_=IdentityName("sn1")),
        params={"mechanism_id": "1"},
    ).mock(return_value=Response(status_code=codes.OK, json=body))
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
        response = client.unstable.identity.get_latest_neurons(mechanism_id=MechanismId(1))

    assert route.called
    assert response.mechanism_id == 1
