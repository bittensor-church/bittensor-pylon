import pytest
from httpx import codes
from pact import Pact

from pylon_client._internal.pylon_commons.types import BlockNumber
from pylon_client._internal.pylon_commons.v1.responses import GetValidatorsResponse
from tests.pact.builders import build_block, build_neuron
from tests.pact.constants import BLOCK_NUMBER, HOTKEY_1, IDENTITY_NAME, NETUID


@pytest.mark.asyncio
async def test_get_validators_success(pact: Pact, get_validators_response_matcher: dict, pylon_client_factory):
    (
        pact.upon_receiving("an identity request for validators at specific block")
        .given(
            "validators exist at block",
            identity_name=IDENTITY_NAME,
            netuid=NETUID,
            block_number=BLOCK_NUMBER,
            validator_count=2,
        )
        .with_request("GET", f"/api/v1/identity/{IDENTITY_NAME}/subnet/{NETUID}/block/{BLOCK_NUMBER}/validators")
        .will_respond_with(codes.OK)
        .with_body(get_validators_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url), logged_in=True)
        async with client:
            response = await client.identity.get_validators(block_number=BlockNumber(BLOCK_NUMBER))

    assert response == GetValidatorsResponse(
        block=build_block(),
        validators=[
            build_neuron(HOTKEY_1, uid=1),
        ],
    )
