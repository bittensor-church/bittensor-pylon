from httpx import codes
from pact import Pact

from pylon_client.artanis import BlockNumber, CommitmentDataHex, Hotkey
from pylon_client.artanis.unstable import GetCommitmentsResponse, HexDataCommitment
from tests.pact.builders import build_block
from tests.pact.constants import BLOCK_NUMBER, COMMITMENT_HEX, HOTKEY_1, HOTKEY_2, IDENTITY_NAME, NETUID


def test_get_commitments_success(pact: Pact, get_commitments_response_matcher: dict, pylon_client_factory):
    (
        pact.upon_receiving("an identity request for all commitments")
        .given("commitments exist", identity_name=IDENTITY_NAME, netuid=NETUID, commitment_count=2)
        .with_request("GET", f"/api/_unstable/identity/{IDENTITY_NAME}/subnet/{NETUID}/block/latest/commitments")
        .will_respond_with(codes.OK)
        .with_body(get_commitments_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url), logged_in=True)
        with client:
            response = client.unstable.identity.get_commitments()

    assert response == GetCommitmentsResponse(
        block=build_block(),
        commitments={
            Hotkey(HOTKEY_1): HexDataCommitment(
                commitment_block_number=BlockNumber(BLOCK_NUMBER),
                hotkey=Hotkey(HOTKEY_1),
                commitment=CommitmentDataHex(COMMITMENT_HEX),
            ),
            Hotkey(HOTKEY_2): HexDataCommitment(
                commitment_block_number=BlockNumber(BLOCK_NUMBER),
                hotkey=Hotkey(HOTKEY_2),
                commitment=CommitmentDataHex(COMMITMENT_HEX),
            ),
        },
    )
