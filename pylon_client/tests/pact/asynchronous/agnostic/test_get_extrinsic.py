import pytest
from httpx import codes
from pact import Pact

from pylon_client._internal.pylon_commons.types import BlockNumber, ExtrinsicIndex
from pylon_client._internal.pylon_commons.v1.responses import GetExtrinsicResponse
from tests.pact.builders import build_extrinsic
from tests.pact.constants import BLOCK_NUMBER, EXTRINSIC_INDEX


@pytest.mark.asyncio
async def test_get_extrinsic_success(pact: Pact, get_extrinsic_response_matcher: dict, pylon_client_factory):
    (
        pact.upon_receiving("a request for a specific extrinsic")
        .given("extrinsic exists", block_number=BLOCK_NUMBER, extrinsic_index=EXTRINSIC_INDEX)
        .with_request("GET", f"/api/v1/block/{BLOCK_NUMBER}/extrinsic/{EXTRINSIC_INDEX}")
        .will_respond_with(codes.OK)
        .with_body(get_extrinsic_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url))
        async with client:
            response = await client.open_access.get_extrinsic(
                block_number=BlockNumber(BLOCK_NUMBER),
                extrinsic_index=ExtrinsicIndex(EXTRINSIC_INDEX),
            )

    assert response == GetExtrinsicResponse(**build_extrinsic().model_dump())
