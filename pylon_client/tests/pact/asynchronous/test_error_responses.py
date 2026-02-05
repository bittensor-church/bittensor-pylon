import pytest
from httpx import codes
from pact import Pact, match

from pylon_client._internal.pylon_commons.exceptions import PylonBadGateway
from pylon_client._internal.pylon_commons.types import BlockNumber, NetUid


@pytest.mark.asyncio
async def test_bad_gateway(pact: Pact, pylon_client_factory):
    (
        pact.upon_receiving("a request")
        .given("block data unavailable", netuid=1, block_number=123)
        .with_request("GET", "/api/v1/subnet/1/block/123/neurons")
        .will_respond_with(codes.BAD_GATEWAY)
        .with_body(
            {"status_code": 502, "detail": match.str("Block 123 data is unavailable")},
            content_type="application/json",
        )
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url))
        async with client:
            with pytest.raises(PylonBadGateway, match=r"^Bad gateway \(HTTP 502\): Block 123 data is unavailable$"):
                await client.open_access.get_neurons(netuid=NetUid(1), block_number=BlockNumber(123))
