import pytest
from httpx import codes
from pact import Pact

from pylon_client.artanis import BlockNumber, CommitmentDataHex, Hotkey
from pylon_client.artanis.unstable import GetCommitmentResponse, HexDataCommitment
from tests.pact.builders import build_block
from tests.pact.constants import BLOCK_NUMBER, COMMITMENT_HEX, HOTKEY_1, IDENTITY_NAME, IDENTITY_TOKEN, NETUID


@pytest.mark.asyncio
async def test_get_commitment_success(pact: Pact, get_commitment_response_matcher: dict, pylon_client_factory):
    (
        pact.upon_receiving("an identity request for a specific commitment")
        .given("commitment exists", identity_name=IDENTITY_NAME, netuid=NETUID, hotkey=HOTKEY_1)
        .with_request(
            "GET", f"/api/_unstable/identity/{IDENTITY_NAME}/subnet/{NETUID}/block/latest/commitments/{HOTKEY_1}"
        )
        .with_header("Authorization", f"Bearer {IDENTITY_TOKEN}")
        .will_respond_with(codes.OK)
        .with_body(get_commitment_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url), logged_in=True)
        async with client:
            response = await client.unstable.identity.get_commitment(hotkey=Hotkey(HOTKEY_1))

    assert response == GetCommitmentResponse(
        block=build_block(),
        commitment=HexDataCommitment(
            commitment_block_number=BlockNumber(BLOCK_NUMBER),
            hotkey=Hotkey(HOTKEY_1),
            commitment=CommitmentDataHex(COMMITMENT_HEX),
        ),
    )
