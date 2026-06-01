from httpx import codes
from pact import Pact

from pylon_client.artanis import Hotkey
from pylon_client.artanis.unstable import GetLatestEvmAssociationsResponse
from tests.pact.builders import build_block, build_evm_association
from tests.pact.constants import HOTKEY_1, HOTKEY_2, IDENTITY_NAME, IDENTITY_TOKEN, NETUID


def test_get_latest_evm_associations_success(
    pact: Pact, get_latest_evm_associations_response_matcher: dict, pylon_client_factory
):
    (
        pact.upon_receiving("an identity request for all latest evm associations")
        .given("evm associations exist", identity_name=IDENTITY_NAME, association_count=2)
        .with_request("GET", f"/api/_unstable/identity/{IDENTITY_NAME}/subnet/{NETUID}/block/latest/evm_associations")
        .with_header("Authorization", f"Bearer {IDENTITY_TOKEN}")
        .will_respond_with(codes.OK)
        .with_body(get_latest_evm_associations_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url), logged_in=True)
        with client:
            response = client.unstable.identity.get_latest_evm_associations()

    assert response == GetLatestEvmAssociationsResponse(
        block=build_block(),
        evm_associations={
            Hotkey(HOTKEY_1): build_evm_association(Hotkey(HOTKEY_1)),
            Hotkey(HOTKEY_2): build_evm_association(Hotkey(HOTKEY_2)),
        },
    )
