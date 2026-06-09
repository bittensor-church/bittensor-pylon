import pytest
from httpx import codes
from pact import Pact

from pylon_client.artanis import Hotkey, NetUid
from pylon_client.artanis.unstable import GetLatestEvmAssociationsResponse
from tests.pact.builders import build_block, build_evm_association
from tests.pact.constants import HOTKEY_1, HOTKEY_2, OPEN_ACCESS_TOKEN


@pytest.mark.asyncio
async def test_get_latest_evm_associations_success(
    pact: Pact, get_latest_evm_associations_response_matcher: dict, pylon_client_factory
):
    (
        pact.upon_receiving("a request for all latest evm associations")
        .given("evm associations exist", netuid=1, association_count=2)
        .with_request("GET", "/api/_unstable/openaccess/subnet/1/block/latest/evm_associations")
        .with_header("Authorization", f"Bearer {OPEN_ACCESS_TOKEN}")
        .will_respond_with(codes.OK)
        .with_body(get_latest_evm_associations_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url))
        async with client:
            response = await client.unstable.open_access.get_latest_evm_associations(netuid=NetUid(1))

    assert response == GetLatestEvmAssociationsResponse(
        block=build_block(),
        evm_associations={
            Hotkey(HOTKEY_1): build_evm_association(Hotkey(HOTKEY_1)),
            Hotkey(HOTKEY_2): build_evm_association(Hotkey(HOTKEY_2)),
        },
    )
