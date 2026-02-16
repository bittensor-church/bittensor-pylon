from httpx import codes
from pact import Pact

from pylon_client._internal.pylon_commons.types import Hotkey
from pylon_client._internal.pylon_commons.v1.responses import GetNeuronsResponse
from tests.pact.builders import build_block, build_neuron
from tests.pact.constants import HOTKEY_1, HOTKEY_2, IDENTITY_NAME, NETUID


def test_get_recent_neurons_success(pact: Pact, get_neurons_response_matcher: dict, pylon_client_factory):
    (
        pact.upon_receiving("an identity request for recent neurons")
        .given("recent neurons exist", identity_name=IDENTITY_NAME, netuid=NETUID, neuron_count=2)
        .with_request("GET", f"/api/v1/identity/{IDENTITY_NAME}/subnet/{NETUID}/block/recent/neurons")
        .will_respond_with(codes.OK)
        .with_body(get_neurons_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url), logged_in=True)
        with client:
            response = client.identity.get_recent_neurons()

    assert response == GetNeuronsResponse(
        block=build_block(),
        neurons={
            Hotkey(HOTKEY_1): build_neuron(HOTKEY_1, uid=1),
            Hotkey(HOTKEY_2): build_neuron(HOTKEY_2, uid=2),
        },
    )
