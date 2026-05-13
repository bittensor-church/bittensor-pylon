from http import HTTPMethod

import pytest

from pylon_client._internal.pylon_commons._unstable.endpoints import Endpoint as EndpointUnstable
from pylon_client.artanis import Hotkey, NetUid
from pylon_client.artanis.unstable import CertificateAlgorithm, GetCertificateResponse
from pylon_client._internal.pylon_commons.types import PublicKey
from tests.unit.synchronous.base_test import OpenAccessEndpointTest


class TestSyncOpenAccessGetCertificate(OpenAccessEndpointTest):
    endpoint = EndpointUnstable.CERTIFICATES_HOTKEY
    route_params = {"netuid": 1, "hotkey": "hotkey1"}
    http_method = HTTPMethod.GET

    def make_endpoint_call(self, client):
        return client.unstable.open_access.get_certificate(netuid=NetUid(1), hotkey=Hotkey("hotkey1"))

    @pytest.fixture
    def success_response(self) -> GetCertificateResponse:
        return GetCertificateResponse(
            algorithm=CertificateAlgorithm.ED25519,
            public_key=PublicKey("ab" * 32),
        )
