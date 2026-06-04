from httpx import codes
from pact import Pact

from pylon_client.artanis import NetUid
from pylon_client.artanis.unstable import GetValidatorsResponse
from tests.pact.builders import build_block, build_neuron
from tests.pact.constants import HOTKEY_1, OPEN_ACCESS_TOKEN


def test_get_latest_validators_success(pact: Pact, get_validators_response_matcher: dict, pylon_client_factory):
    (
        pact.upon_receiving("a request for latest validators")
        .given("validators exist", netuid=1, validator_count=2)
        .with_request("GET", "/api/_unstable/openaccess/subnet/1/block/latest/validators")
        .with_header("Authorization", f"Bearer {OPEN_ACCESS_TOKEN}")
        .will_respond_with(codes.OK)
        .with_body(get_validators_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url))
        with client:
            response = client.unstable.open_access.get_latest_validators(netuid=NetUid(1))

    assert response == GetValidatorsResponse(
        block=build_block(),
        validators=[
            build_neuron(HOTKEY_1, uid=1),
        ],
    )
