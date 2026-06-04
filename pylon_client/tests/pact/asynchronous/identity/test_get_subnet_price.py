import pytest
from httpx import codes
from pact import Pact

from pylon_client.artanis import BlockNumber
from tests.pact.builders import build_price
from tests.pact.constants import BLOCK_NUMBER, IDENTITY_NAME, IDENTITY_TOKEN, NETUID


@pytest.mark.asyncio
async def test_get_latest_price_success(pact: Pact, get_price_response_matcher: dict, pylon_client_factory):
    (
        pact.upon_receiving("an identity request for latest subnet price")
        .given("price exists", identity_name=IDENTITY_NAME, netuid=NETUID)
        .with_request("GET", f"/api/_unstable/identity/{IDENTITY_NAME}/subnet/{NETUID}/block/latest/price")
        .with_header("Authorization", f"Bearer {IDENTITY_TOKEN}")
        .will_respond_with(codes.OK)
        .with_body(get_price_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url), logged_in=True)
        async with client:
            response = await client.unstable.identity.get_latest_price()

    assert response == build_price(netuid=NETUID)


@pytest.mark.asyncio
async def test_get_price_success(pact: Pact, get_price_response_matcher: dict, pylon_client_factory):
    (
        pact.upon_receiving("an identity request for subnet price at specific block")
        .given("price exists at block", identity_name=IDENTITY_NAME, netuid=NETUID, block_number=BLOCK_NUMBER)
        .with_request("GET", f"/api/_unstable/identity/{IDENTITY_NAME}/subnet/{NETUID}/block/{BLOCK_NUMBER}/price")
        .with_header("Authorization", f"Bearer {IDENTITY_TOKEN}")
        .will_respond_with(codes.OK)
        .with_body(get_price_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url), logged_in=True)
        async with client:
            response = await client.unstable.identity.get_price(block_number=BlockNumber(BLOCK_NUMBER))

    assert response == build_price(netuid=NETUID)
