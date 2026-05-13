from http import HTTPMethod

import pytest

from pylon_client._internal.pylon_commons._unstable.endpoints import Endpoint as EndpointUnstable
from pylon_client.artanis import Hotkey
from pylon_client.artanis.unstable import CertificateAlgorithm, GetCertificateResponse, NeuronCertificate
from pylon_client._internal.pylon_commons.types import PublicKey
from tests.unit.synchronous.base_test import IdentityEndpointTest


class TestSyncIdentityGetCertificate(IdentityEndpointTest):
    endpoint = EndpointUnstable.CERTIFICATES_HOTKEY
    route_params = {"identity_name": "sn1", "netuid": 1, "hotkey": "hotkey1"}
    http_method = HTTPMethod.GET

    def make_endpoint_call(self, client):
        return client.unstable.identity.get_certificate(hotkey=Hotkey("hotkey1"))

    @pytest.fixture
    def success_response(self) -> GetCertificateResponse:
        return GetCertificateResponse(
            algorithm=CertificateAlgorithm.ED25519,
            public_key=PublicKey("ab" * 32),
        )
