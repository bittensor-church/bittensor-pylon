from httpx import codes
from pact import Pact

from pylon_client.artanis.unstable import SetRevealedCommitmentResponse
from tests.pact.constants import (
    COMMITMENT_HEX,
    IDENTITY_NAME,
    IDENTITY_TOKEN,
    NETUID,
)


def test_set_revealed_commitment_success(
    pact: Pact, post_revealed_commitment_response_matcher: dict, pylon_client_factory
):
    blocks_until_reveal = 360
    (
        pact.upon_receiving("an identity request to set revealed commitment")
        .given("revealed commitment can be set", identity_name=IDENTITY_NAME, netuid=NETUID)
        .with_request("POST", f"/api/_unstable/identity/{IDENTITY_NAME}/subnet/{NETUID}/commitments/revealed")
        .with_header("Authorization", f"Bearer {IDENTITY_TOKEN}")
        .with_body(
            {"commitment": COMMITMENT_HEX, "blocks_until_reveal": blocks_until_reveal}, content_type="application/json"
        )
        .will_respond_with(codes.CREATED)
        .with_body(post_revealed_commitment_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url), logged_in=True)
        with client:
            response = client.unstable.identity.set_revealed_commitment(
                commitment=COMMITMENT_HEX, blocks_until_reveal=blocks_until_reveal
            )

    assert response == SetRevealedCommitmentResponse(reveal_round=123456)
