from httpx import codes
from pact import Pact

from pylon_client.artanis import BlockNumber, CommitmentDataHex, Hotkey, NetUid
from pylon_client.artanis.unstable import Commitment, GetCommitmentsResponse
from tests.pact.builders import build_block
from tests.pact.constants import BLOCK_NUMBER, COMMITMENT_HEX, HOTKEY_1, HOTKEY_2


def test_get_commitments_success(pact: Pact, get_commitments_response_matcher: dict, pylon_client_factory):
    (
        pact.upon_receiving("a request for all commitments")
        .given("commitments exist", netuid=1, commitment_count=2)
        .with_request("GET", "/api/_unstable/subnet/1/block/latest/commitments")
        .will_respond_with(codes.OK)
        .with_body(get_commitments_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url))
        with client:
            response = client.unstable.open_access.get_commitments(netuid=NetUid(1))

    assert response == GetCommitmentsResponse(
        block=build_block(),
        commitments={
            Hotkey(HOTKEY_1): Commitment(
                commitment_block_number=BlockNumber(BLOCK_NUMBER),
                hotkey=Hotkey(HOTKEY_1),
                commitment=CommitmentDataHex(COMMITMENT_HEX),
            ),
            Hotkey(HOTKEY_2): Commitment(
                commitment_block_number=BlockNumber(BLOCK_NUMBER),
                hotkey=Hotkey(HOTKEY_2),
                commitment=CommitmentDataHex(COMMITMENT_HEX),
            ),
        },
    )
