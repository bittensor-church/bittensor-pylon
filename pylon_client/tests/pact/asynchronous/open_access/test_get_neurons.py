import pytest
from httpx import codes
from pact import Pact

from pylon_client._internal.pylon_commons.types import BlockNumber, Hotkey, NetUid
from pylon_client._internal.pylon_commons.v1.responses import GetNeuronsResponse
from tests.pact.builders import build_block, build_neuron
from tests.pact.constants import BLOCK_NUMBER, HOTKEY_1, HOTKEY_2


@pytest.mark.asyncio
async def test_get_neurons_success(pact: Pact, get_neurons_response_matcher: dict, pylon_client_factory):
    (
        pact.upon_receiving("a request for neurons at specific block")
        .given("neurons exist at block", netuid=1, block_number=BLOCK_NUMBER, neuron_count=2)
        .with_request("GET", f"/api/v1/subnet/1/block/{BLOCK_NUMBER}/neurons")
        .will_respond_with(codes.OK)
        .with_body(get_neurons_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url))
        async with client:
            response = await client.open_access.get_neurons(netuid=NetUid(1), block_number=BlockNumber(BLOCK_NUMBER))

    assert response == GetNeuronsResponse(
        block=build_block(),
        neurons={
            Hotkey(HOTKEY_1): build_neuron(HOTKEY_1, uid=1),
            Hotkey(HOTKEY_2): build_neuron(HOTKEY_2, uid=2),
        },
    )
