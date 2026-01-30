import pytest
from httpx import codes
from pact import Pact

from pylon_client._internal.pylon_commons._unstable.responses import GetCommitmentsResponseUnstable
from pylon_client._internal.pylon_commons.types import Hotkey
from tests.pact.builders import build_block, build_commitment
from tests.pact.constants import HOTKEY_1, HOTKEY_2, IDENTITY_NAME, NETUID


@pytest.mark.asyncio
async def test_get_commitments_unstable_success(
    pact: Pact, get_commitments_response_unstable_matcher: dict, pylon_client_factory
):
    (
        pact.upon_receiving("an identity request for all commitments unstable")
        .given("commitments exist", identity_name=IDENTITY_NAME, netuid=NETUID, commitment_count=2)
        .with_request("GET", f"/api/_unstable/identity/{IDENTITY_NAME}/subnet/{NETUID}/block/latest/commitments")
        .will_respond_with(codes.OK)
        .with_body(get_commitments_response_unstable_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url), logged_in=True)
        async with client:
            response = await client.unstable.identity.get_commitments()

    assert response == GetCommitmentsResponseUnstable(
        block=build_block(),
        commitments={
            Hotkey(HOTKEY_1): build_commitment(HOTKEY_1),
            Hotkey(HOTKEY_2): build_commitment(HOTKEY_2),
        },
    )
