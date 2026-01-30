import pytest
from httpx import codes
from pact import Pact

from pylon_client._internal.pylon_commons._unstable.responses import GetCommitmentsResponseUnstable
from pylon_client._internal.pylon_commons.types import Hotkey, NetUid
from tests.pact.builders import build_block, build_commitment
from tests.pact.constants import HOTKEY_1, HOTKEY_2


@pytest.mark.asyncio
async def test_get_commitments_unstable_success(
    pact: Pact, get_commitments_response_unstable_matcher: dict, pylon_client_factory
):
    (
        pact.upon_receiving("a request for all commitments unstable")
        .given("commitments exist", netuid=1, commitment_count=2)
        .with_request("GET", "/api/_unstable/subnet/1/block/latest/commitments")
        .will_respond_with(codes.OK)
        .with_body(get_commitments_response_unstable_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url))
        async with client:
            response = await client.unstable.open_access.get_commitments(netuid=NetUid(1))

    assert response == GetCommitmentsResponseUnstable(
        block=build_block(),
        commitments={
            Hotkey(HOTKEY_1): build_commitment(HOTKEY_1),
            Hotkey(HOTKEY_2): build_commitment(HOTKEY_2),
        },
    )
