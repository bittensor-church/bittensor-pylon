from httpx import codes
from pact import Pact

from pylon_client._internal.pylon_commons.types import CommitmentDataHex
from pylon_client._internal.pylon_commons.v1.responses import SetCommitmentResponse
from tests.pact.constants import COMMITMENT_HEX, IDENTITY_NAME, NETUID


def test_set_commitment_success(pact: Pact, post_commitment_response_matcher: dict, pylon_client_factory):
    (
        pact.upon_receiving("an identity request to set commitment")
        .given("commitment can be set", identity_name=IDENTITY_NAME, netuid=NETUID)
        .with_request("POST", f"/api/v1/identity/{IDENTITY_NAME}/subnet/{NETUID}/commitments")
        .with_body({"commitment": COMMITMENT_HEX}, content_type="application/json")
        .will_respond_with(codes.CREATED)
        .with_body(post_commitment_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url), logged_in=True)
        with client:
            response = client.identity.set_commitment(commitment=CommitmentDataHex(COMMITMENT_HEX))

    assert response == SetCommitmentResponse()
