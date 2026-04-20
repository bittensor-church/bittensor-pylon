from httpx import codes
from pact import Pact

from pylon_client.artanis import BlockNumber, CommitmentDataHex, Hotkey, NetUid
from pylon_client.artanis.unstable import GetCommitmentResponse, HexDataCommitment
from tests.pact.builders import build_block
from tests.pact.constants import BLOCK_NUMBER, COMMITMENT_HEX, HOTKEY_1, OPEN_ACCESS_TOKEN


def test_get_commitment_success(pact: Pact, get_commitment_response_matcher: dict, pylon_client_factory):
    (
        pact.upon_receiving("a request for a specific commitment")
        .given("commitment exists", netuid=1, hotkey=HOTKEY_1)
        .with_request("GET", f"/api/_unstable/subnet/1/block/latest/commitments/{HOTKEY_1}")
        .with_header("Authorization", f"Bearer {OPEN_ACCESS_TOKEN}")
        .will_respond_with(codes.OK)
        .with_body(get_commitment_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url))
        with client:
            response = client.unstable.open_access.get_commitment(netuid=NetUid(1), hotkey=Hotkey(HOTKEY_1))

    assert response == GetCommitmentResponse(
        block=build_block(),
        commitment=HexDataCommitment(
            commitment_block_number=BlockNumber(BLOCK_NUMBER),
            hotkey=Hotkey(HOTKEY_1),
            commitment=CommitmentDataHex(COMMITMENT_HEX),
        ),
    )
