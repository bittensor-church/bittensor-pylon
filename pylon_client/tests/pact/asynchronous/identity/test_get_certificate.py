import pytest
from httpx import codes
from pact import Pact

from pylon_client.artanis import Hotkey
from pylon_client.artanis.unstable import CertificateAlgorithm, GetCertificateResponse
from pylon_client._internal.pylon_commons.types import PublicKey
from tests.pact.constants import HOTKEY_1, IDENTITY_NAME, IDENTITY_TOKEN, NETUID, PUBLIC_KEY


@pytest.mark.asyncio
async def test_get_certificate_success(pact: Pact, get_certificate_response_matcher: dict, pylon_client_factory):
    (
        pact.upon_receiving("an identity request for a certificate")
        .given("certificate exists", identity_name=IDENTITY_NAME, netuid=NETUID, hotkey=HOTKEY_1)
        .with_request("GET", f"/api/_unstable/identity/{IDENTITY_NAME}/subnet/{NETUID}/block/latest/certificates/{HOTKEY_1}")
        .with_header("Authorization", f"Bearer {IDENTITY_TOKEN}")
        .will_respond_with(codes.OK)
        .with_body(get_certificate_response_matcher, content_type="application/json")
    )

    with pact.serve() as srv:
        client = pylon_client_factory(str(srv.url), logged_in=True)
        async with client:
            response = await client.unstable.identity.get_certificate(hotkey=Hotkey(HOTKEY_1))

    assert response == GetCertificateResponse(
        algorithm=CertificateAlgorithm.ED25519,
        public_key=PublicKey(PUBLIC_KEY),
    )
