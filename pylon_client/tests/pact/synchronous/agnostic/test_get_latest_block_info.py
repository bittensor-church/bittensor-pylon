from httpx import codes
from pact import Pact

from pylon_client._internal.pylon_commons.v1.responses import GetLatestBlockInfoResponse
from tests.pact.builders import build_block_info_bag


def test_get_latest_block_info_success(pact: Pact, get_latest_block_info_response_matcher: dict, pylon_client_factory):
    (
        pact.upon_receiving("a request for latest block info")
        .given("latest block info exists")
        .with_request("GET", "/api/v1/block/latest")
        .will_respond_with(codes.OK)
        .with_body(get_latest_block_info_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url))
        with client:
            response = client.open_access.get_latest_block_info()

    assert response == GetLatestBlockInfoResponse(**build_block_info_bag().model_dump())
