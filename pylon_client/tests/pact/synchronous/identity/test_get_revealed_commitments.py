from httpx import codes
from pact import Pact

from pylon_client.artanis import BlockNumber, Hotkey, RevealedCommitmentData
from pylon_client.artanis.unstable import GetRevealedCommitmentsResponse, RevealedCommitment
from tests.pact.builders import build_block
from tests.pact.constants import (
    BLOCK_NUMBER,
    COMMITMENT_HEX,
    HOTKEY_1,
    IDENTITY_NAME,
    IDENTITY_TOKEN,
    NETUID,
)


def test_get_revealed_commitments_success(
    pact: Pact, get_own_revealed_commitments_response_matcher: dict, pylon_client_factory
):
    (
        pact.upon_receiving("an identity request for revealed commitments")
        .given("revealed commitments exist", identity_name=IDENTITY_NAME, netuid=NETUID, hotkey=HOTKEY_1)
        .with_request(
            "GET",
            f"/api/_unstable/identity/{IDENTITY_NAME}/subnet/{NETUID}/block/latest/commitments/revealed/{HOTKEY_1}",
        )
        .with_header("Authorization", f"Bearer {IDENTITY_TOKEN}")
        .will_respond_with(codes.OK)
        .with_body(get_own_revealed_commitments_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url), logged_in=True)
        with client:
            response = client.unstable.identity.get_revealed_commitments(hotkey=Hotkey(HOTKEY_1))

    assert response == GetRevealedCommitmentsResponse(
        block=build_block(),
        commitments=[
            RevealedCommitment(
                reveal_block_number=BlockNumber(BLOCK_NUMBER),
                hotkey=Hotkey(HOTKEY_1),
                commitment=RevealedCommitmentData(COMMITMENT_HEX),
            )
        ],
    )
