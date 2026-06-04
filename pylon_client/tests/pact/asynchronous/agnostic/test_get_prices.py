import pytest
from httpx import codes
from pact import Pact

from pylon_client.artanis import BlockNumber
from tests.pact.builders import build_prices
from tests.pact.constants import BLOCK_NUMBER


@pytest.mark.asyncio
async def test_get_latest_prices_success(pact: Pact, get_prices_response_matcher: dict, pylon_client_factory):
    (
        pact.upon_receiving("a request for latest prices")
        .given("prices exist")
        .with_request("GET", "/api/_unstable/openaccess/block/latest/prices")
        .will_respond_with(codes.OK)
        .with_body(get_prices_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url))
        async with client:
            response = await client.unstable.open_access.get_latest_prices()

    assert response == build_prices()


@pytest.mark.asyncio
async def test_get_prices_success(pact: Pact, get_prices_response_matcher: dict, pylon_client_factory):
    (
        pact.upon_receiving("a request for prices at specific block")
        .given("prices exist at block", block_number=BLOCK_NUMBER)
        .with_request("GET", f"/api/_unstable/openaccess/block/{BLOCK_NUMBER}/prices")
        .will_respond_with(codes.OK)
        .with_body(get_prices_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url))
        async with client:
            response = await client.unstable.open_access.get_prices(block_number=BlockNumber(BLOCK_NUMBER))

    assert response == build_prices()
