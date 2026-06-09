from httpx import codes
from pact import Pact

from pylon_client.artanis import BlockNumber, NetUid
from tests.pact.builders import build_price
from tests.pact.constants import BLOCK_NUMBER, NETUID, OPEN_ACCESS_TOKEN


def test_get_latest_price_success(pact: Pact, get_price_response_matcher: dict, pylon_client_factory):
    (
        pact.upon_receiving("a request for latest subnet price")
        .given("price exists", netuid=NETUID)
        .with_request("GET", f"/api/_unstable/openaccess/subnet/{NETUID}/block/latest/price")
        .with_header("Authorization", f"Bearer {OPEN_ACCESS_TOKEN}")
        .will_respond_with(codes.OK)
        .with_body(get_price_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url))
        with client:
            response = client.unstable.open_access.get_latest_price(netuid=NetUid(NETUID))

    assert response == build_price(netuid=NETUID)


def test_get_price_success(pact: Pact, get_price_response_matcher: dict, pylon_client_factory):
    (
        pact.upon_receiving("a request for subnet price at specific block")
        .given("price exists at block", netuid=NETUID, block_number=BLOCK_NUMBER)
        .with_request("GET", f"/api/_unstable/openaccess/subnet/{NETUID}/block/{BLOCK_NUMBER}/price")
        .with_header("Authorization", f"Bearer {OPEN_ACCESS_TOKEN}")
        .will_respond_with(codes.OK)
        .with_body(get_price_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url))
        with client:
            response = client.unstable.open_access.get_price(
                netuid=NetUid(NETUID), block_number=BlockNumber(BLOCK_NUMBER)
            )

    assert response == build_price(netuid=NETUID)
