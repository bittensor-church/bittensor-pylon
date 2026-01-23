from httpx import codes
from pact import Pact

from pylon_client._internal.pylon_commons.responses import SetWeightsResponse
from pylon_client._internal.pylon_commons.types import Hotkey, Weight
from tests.pact.constants import HOTKEY_1, HOTKEY_2, IDENTITY_NAME, NETUID


def test_put_weights_success(pact: Pact, put_weights_response_matcher: dict, pylon_client_factory):
    (
        pact.upon_receiving("an identity request to set weights")
        .given("weights can be set", identity_name=IDENTITY_NAME, netuid=NETUID)
        .with_request("PUT", f"/api/v1/identity/{IDENTITY_NAME}/subnet/{NETUID}/weights")
        .with_body({"weights": {HOTKEY_1: 0.6, HOTKEY_2: 0.4}}, content_type="application/json")
        .will_respond_with(codes.OK)
        .with_body(put_weights_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url), logged_in=True)
        with client:
            response = client.identity.put_weights(
                weights={
                    Hotkey(HOTKEY_1): Weight(0.6),
                    Hotkey(HOTKEY_2): Weight(0.4),
                }
            )

    assert response == SetWeightsResponse()
