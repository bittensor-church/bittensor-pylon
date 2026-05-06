import pytest
from httpx import codes
from pact import Pact

from pylon_client.artanis import BlockNumber, Hotkey, RevealedCommitmentData
from pylon_client.artanis.unstable import GetAllRevealedCommitmentsResponse, RevealedCommitment
from tests.pact.builders import build_block
from tests.pact.constants import (
    BLOCK_NUMBER,
    COMMITMENT_HEX,
    HOTKEY_1,
    HOTKEY_2,
    IDENTITY_NAME,
    IDENTITY_TOKEN,
    NETUID,
)


@pytest.mark.asyncio
async def test_get_all_revealed_commitments_success(
    pact: Pact, get_revealed_commitments_response_matcher: dict, pylon_client_factory
):
    (
        pact.upon_receiving("an identity request for all revealed commitments")
        .given("revealed commitments exist", identity_name=IDENTITY_NAME, netuid=NETUID)
        .with_request(
            "GET", f"/api/_unstable/identity/{IDENTITY_NAME}/subnet/{NETUID}/block/latest/commitments/revealed"
        )
        .with_header("Authorization", f"Bearer {IDENTITY_TOKEN}")
        .will_respond_with(codes.OK)
        .with_body(get_revealed_commitments_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url), logged_in=True)
        async with client:
            response = await client.unstable.identity.get_all_revealed_commitments()

    assert response == GetAllRevealedCommitmentsResponse(
        block=build_block(),
        commitments={
            Hotkey(HOTKEY_1): [
                RevealedCommitment(
                    reveal_block_number=BlockNumber(BLOCK_NUMBER),
                    hotkey=Hotkey(HOTKEY_1),
                    commitment=RevealedCommitmentData(COMMITMENT_HEX),
                )
            ],
            Hotkey(HOTKEY_2): [
                RevealedCommitment(
                    reveal_block_number=BlockNumber(BLOCK_NUMBER),
                    hotkey=Hotkey(HOTKEY_2),
                    commitment=RevealedCommitmentData(COMMITMENT_HEX),
                )
            ],
        },
    )
