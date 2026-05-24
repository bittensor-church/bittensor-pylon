import pytest
from httpx import codes
from pact import Pact

from pylon_client._internal.pylon_commons.types import PublicKey
from pylon_client.artanis import Hotkey, NetUid
from pylon_client.artanis.unstable import CertificateAlgorithm, GetCertificateResponse
from tests.pact.constants import HOTKEY_1, NETUID, OPEN_ACCESS_TOKEN, PUBLIC_KEY


@pytest.mark.asyncio
async def test_get_certificate_success(pact: Pact, get_certificate_response_matcher: dict, pylon_client_factory):
    (
        pact.upon_receiving("a request for a certificate")
        .given("certificate exists", netuid=NETUID, hotkey=HOTKEY_1)
        .with_request("GET", f"/api/_unstable/openaccess/subnet/{NETUID}/block/latest/certificates/{HOTKEY_1}")
        .with_header("Authorization", f"Bearer {OPEN_ACCESS_TOKEN}")
        .will_respond_with(codes.OK)
        .with_body(get_certificate_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url))
        async with client:
            response = await client.unstable.open_access.get_certificate(netuid=NetUid(NETUID), hotkey=Hotkey(HOTKEY_1))

    assert response == GetCertificateResponse(
        algorithm=CertificateAlgorithm.ED25519,
        public_key=PublicKey(PUBLIC_KEY),
    )
