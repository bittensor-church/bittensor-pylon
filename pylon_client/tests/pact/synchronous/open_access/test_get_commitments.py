from httpx import codes
from pact import Pact

from pylon_client._internal.pylon_commons.responses import GetCommitmentsResponse
from pylon_client._internal.pylon_commons.types import CommitmentDataHex, Hotkey, NetUid
from tests.pact.builders import build_block
from tests.pact.constants import COMMITMENT_HEX, HOTKEY_1, HOTKEY_2


def test_get_commitments_success(pact: Pact, get_commitments_response_matcher: dict, pylon_client_factory):
    (
        pact.upon_receiving("a request for all commitments")
        .given("commitments exist", netuid=1, commitment_count=2)
        .with_request("GET", "/api/v1/subnet/1/block/latest/commitments")
        .will_respond_with(codes.OK)
        .with_body(get_commitments_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url))
        with client:
            response = client.open_access.get_commitments(netuid=NetUid(1))

    assert response == GetCommitmentsResponse(
        block=build_block(),
        commitments={
            Hotkey(HOTKEY_1): CommitmentDataHex(COMMITMENT_HEX),
            Hotkey(HOTKEY_2): CommitmentDataHex(COMMITMENT_HEX),
        },
    )
