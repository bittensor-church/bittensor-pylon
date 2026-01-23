from httpx import codes
from pact import Pact

from pylon_client._internal.pylon_commons.responses import GetCommitmentsResponse
from pylon_client._internal.pylon_commons.types import CommitmentDataHex, Hotkey
from tests.pact.builders import build_block
from tests.pact.constants import COMMITMENT_HEX, HOTKEY_1, HOTKEY_2, IDENTITY_NAME, NETUID


def test_get_commitments_success(pact: Pact, get_commitments_response_matcher: dict, pylon_client_factory):
    (
        pact.upon_receiving("an identity request for all commitments")
        .given("commitments exist", identity_name=IDENTITY_NAME, netuid=NETUID, commitment_count=2)
        .with_request("GET", f"/api/v1/identity/{IDENTITY_NAME}/subnet/{NETUID}/block/latest/commitments")
        .will_respond_with(codes.OK)
        .with_body(get_commitments_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url), logged_in=True)
        with client:
            response = client.identity.get_commitments()

    assert response == GetCommitmentsResponse(
        block=build_block(),
        commitments={
            Hotkey(HOTKEY_1): CommitmentDataHex(COMMITMENT_HEX),
            Hotkey(HOTKEY_2): CommitmentDataHex(COMMITMENT_HEX),
        },
    )
