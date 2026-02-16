from httpx import codes
from pact import Pact

from pylon_client._internal.pylon_commons.types import BlockNumber, CommitmentDataHex, Hotkey
from pylon_client._internal.pylon_commons.v1.responses import GetCommitmentResponse
from tests.pact.builders import build_block
from tests.pact.constants import BLOCK_NUMBER, COMMITMENT_HEX, HOTKEY_1, IDENTITY_NAME, NETUID


def test_get_own_commitment_success(pact: Pact, get_commitment_response_matcher: dict, pylon_client_factory):
    (
        pact.upon_receiving("an identity request for own commitment")
        .given("own commitment exists", identity_name=IDENTITY_NAME, netuid=NETUID, hotkey=HOTKEY_1)
        .with_request("GET", f"/api/v1/identity/{IDENTITY_NAME}/subnet/{NETUID}/block/latest/commitments/self")
        .will_respond_with(codes.OK)
        .with_body(get_commitment_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url), logged_in=True)
        with client:
            response = client.identity.get_own_commitment()

    assert response == GetCommitmentResponse(
        block=build_block(),
        commitment_block_number=BlockNumber(BLOCK_NUMBER),
        hotkey=Hotkey(HOTKEY_1),
        commitment=CommitmentDataHex(COMMITMENT_HEX),
    )
