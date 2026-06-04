import pytest
from httpx import Response, codes

from pylon_client._internal.pylon_commons._unstable.endpoints import Endpoint
from pylon_client._internal.pylon_commons.types import Hotkey, IdentityName, NetUid
from pylon_client.artanis import AsyncPylonClient, PylonNetuidMismatch
from pylon_client.artanis.unstable import GetNeuronsResponse

IDENTITIES_URL = Endpoint.IDENTITIES.absolute_url(is_public_=True)


def _neurons_url(netuid: int) -> str:
    return Endpoint.LATEST_NEURONS.absolute_url(netuid_=NetUid(netuid), identity_name_=IdentityName("sn1"))


def _identities_response(netuid: int) -> Response:
    return Response(status_code=codes.OK, json={"identities": {"sn1": netuid}})


@pytest.fixture
def neurons_response(block_factory, neuron_factory):
    return GetNeuronsResponse(block=block_factory.build(), neurons={Hotkey("hk1"): neuron_factory.build()})


@pytest.mark.asyncio
async def test_retries_with_refreshed_netuid_on_308(
    identity_client: AsyncPylonClient,
    service_mock,
    neurons_response: GetNeuronsResponse,
):
    """
    Test that the client re-fetches identities and retries on 308 (netuid mismatch).
    """
    identities_route = service_mock.get(IDENTITIES_URL).mock(
        side_effect=[
            _identities_response(netuid=1),
            _identities_response(netuid=2),
        ]
    )
    neurons_old = service_mock.get(_neurons_url(1)).mock(return_value=Response(status_code=codes.PERMANENT_REDIRECT))
    neurons_new = service_mock.get(_neurons_url(2)).mock(
        return_value=Response(status_code=codes.OK, json=neurons_response.model_dump(mode="json"))
    )

    async with identity_client:
        result = await identity_client.unstable.identity.get_latest_neurons()

    assert result == neurons_response
    assert identities_route.call_count == 2
    assert neurons_old.call_count == 1
    assert neurons_new.call_count == 1


@pytest.mark.asyncio
async def test_raises_on_308_after_refresh(
    identity_client: AsyncPylonClient,
    service_mock,
):
    """
    Test that 308 after refresh raises PylonNetuidMismatch (no infinite retry loop).
    """
    service_mock.get(IDENTITIES_URL).mock(
        side_effect=[
            _identities_response(netuid=1),
            _identities_response(netuid=2),
        ]
    )
    service_mock.get(_neurons_url(1)).mock(return_value=Response(status_code=codes.PERMANENT_REDIRECT))
    service_mock.get(_neurons_url(2)).mock(return_value=Response(status_code=codes.PERMANENT_REDIRECT))

    async with identity_client:
        with pytest.raises(PylonNetuidMismatch, match=r"Netuid mismatch \(HTTP 308\)"):
            await identity_client.unstable.identity.get_latest_neurons()
