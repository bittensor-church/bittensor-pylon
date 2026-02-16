from httpx import codes
from pact import Pact

from pylon_client._internal.pylon_commons.v1.responses import GetValidatorsResponse
from tests.pact.builders import build_block, build_neuron
from tests.pact.constants import HOTKEY_1, IDENTITY_NAME, NETUID


def test_get_latest_validators_success(pact: Pact, get_validators_response_matcher: dict, pylon_client_factory):
    (
        pact.upon_receiving("an identity request for latest validators")
        .given("validators exist", identity_name=IDENTITY_NAME, netuid=NETUID, validator_count=2)
        .with_request("GET", f"/api/v1/identity/{IDENTITY_NAME}/subnet/{NETUID}/block/latest/validators")
        .will_respond_with(codes.OK)
        .with_body(get_validators_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url), logged_in=True)
        with client:
            response = client.identity.get_latest_validators()

    assert response == GetValidatorsResponse(
        block=build_block(),
        validators=[
            build_neuron(HOTKEY_1, uid=1),
        ],
    )
