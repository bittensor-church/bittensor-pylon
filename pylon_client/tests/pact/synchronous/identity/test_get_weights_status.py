from httpx import codes
from pact import Pact

from pylon_client.artanis import MechanismId
from pylon_client.artanis.unstable import GetWeightsStatusResponse
from tests.pact.constants import IDENTITY_NAME, IDENTITY_TOKEN, NETUID


def test_get_weights_status_success(pact: Pact, get_weights_status_response_fixture: dict, pylon_client_factory):
    mechanism_id = 1
    block_number = 123
    (
        pact.upon_receiving("an identity request to get weights status")
        .given("weights status can be retrieved", identity_name=IDENTITY_NAME, netuid=NETUID)
        .with_request(
            "GET",
            f"/api/_unstable/identity/{IDENTITY_NAME}/subnet/{NETUID}/mechanism/{mechanism_id}/block/{block_number}/weights/status",
        )
        .with_header("Authorization", f"Bearer {IDENTITY_TOKEN}")
        .will_respond_with(codes.OK)
        .with_body(get_weights_status_response_fixture, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url), logged_in=True)
        with client:
            response = client.unstable.identity.get_weights_status(
                mechanism_id=MechanismId(mechanism_id),
                block_number=block_number,
            )

    assert response == GetWeightsStatusResponse(weights_submitted=False)
