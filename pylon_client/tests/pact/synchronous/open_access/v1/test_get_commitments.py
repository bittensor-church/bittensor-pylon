from httpx import codes
from pact import Pact

from pylon_client.artanis import CommitmentDataHex, Hotkey, NetUid
from pylon_client.artanis.v1 import GetCommitmentsResponse
from tests.pact.builders import build_block
from tests.pact.constants import COMMITMENT_HEX, HOTKEY_1, HOTKEY_2, OPEN_ACCESS_TOKEN


def test_get_commitments_v1_success(pact: Pact, get_commitments_v1_response_matcher: dict, pylon_client_factory):
    (
        pact.upon_receiving("a v1 request for all commitments")
        .given("commitments exist", netuid=1, commitment_count=2)
        .with_request("GET", "/api/v1/subnet/1/block/latest/commitments")
        .with_header("Authorization", f"Bearer {OPEN_ACCESS_TOKEN}")
        .will_respond_with(codes.OK)
        .with_body(get_commitments_v1_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url))
        with client:
            response = client.v1.open_access.get_commitments(netuid=NetUid(1))

    assert response == GetCommitmentsResponse(
        block=build_block(),
        commitments={
            Hotkey(HOTKEY_1): CommitmentDataHex(COMMITMENT_HEX),
            Hotkey(HOTKEY_2): CommitmentDataHex(COMMITMENT_HEX),
        },
    )
