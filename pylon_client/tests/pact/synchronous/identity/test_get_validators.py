from httpx import codes
from pact import Pact

from pylon_client.artanis import BlockNumber
from pylon_client.artanis.unstable import GetValidatorsResponse
from tests.pact.builders import build_block, build_neuron
from tests.pact.constants import BLOCK_NUMBER, HOTKEY_1, IDENTITY_NAME, IDENTITY_TOKEN, NETUID


def test_get_validators_success(pact: Pact, get_validators_response_matcher: dict, pylon_client_factory):
    (
        pact.upon_receiving("an identity request for validators at specific block")
        .given(
            "validators exist at block",
            identity_name=IDENTITY_NAME,
            netuid=NETUID,
            block_number=BLOCK_NUMBER,
            validator_count=2,
        )
        .with_request("GET", f"/api/_unstable/identity/{IDENTITY_NAME}/subnet/{NETUID}/block/{BLOCK_NUMBER}/validators")
        .with_header("Authorization", f"Bearer {IDENTITY_TOKEN}")
        .will_respond_with(codes.OK)
        .with_body(get_validators_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url), logged_in=True)
        with client:
            response = client.unstable.identity.get_validators(block_number=BlockNumber(BLOCK_NUMBER))

    assert response == GetValidatorsResponse(
        block=build_block(),
        validators=[
            build_neuron(HOTKEY_1, uid=1),
        ],
    )
