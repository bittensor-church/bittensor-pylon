from http import HTTPMethod

import pytest
from httpx import Response, codes

from pylon_client._internal.pylon_commons.endpoints import Endpoint
from pylon_client._internal.pylon_commons.models import ExtrinsicCall, ExtrinsicCallArg
from pylon_client._internal.pylon_commons.responses import GetExtrinsicResponse
from pylon_client._internal.pylon_commons.types import BlockNumber, ExtrinsicHash, ExtrinsicIndex, ExtrinsicLength
from tests.unit.synchronous.base_test import IdentityEndpointTest


class TestSyncIdentityGetExtrinsic(IdentityEndpointTest):
    endpoint = Endpoint.EXTRINSIC
    route_params = {"block_number": 1000, "extrinsic_index": 0}
    http_method = HTTPMethod.GET

    def make_endpoint_call(self, client):
        return client.identity.get_extrinsic(block_number=BlockNumber(1000), extrinsic_index=ExtrinsicIndex(0))

    @pytest.fixture
    def success_response(self) -> GetExtrinsicResponse:
        return GetExtrinsicResponse(
            block_number=BlockNumber(1000),
            extrinsic_index=ExtrinsicIndex(0),
            extrinsic_hash=ExtrinsicHash("0xabc123"),
            extrinsic_length=ExtrinsicLength(100),
            address="5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
            call=ExtrinsicCall(
                call_module="Balances",
                call_function="transfer",
                call_args=[
                    ExtrinsicCallArg(
                        name="dest", type="AccountId", value="5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"
                    ),
                    ExtrinsicCallArg(name="value", type="Balance", value=1_000_000_000),
                ],
            ),
        )

    def test_unsigned_extrinsic(self, pylon_client, service_mock, route_mock):
        """
        Test getting an unsigned extrinsic (address is None).
        """
        self._setup_login_mock(service_mock)

        expected_response = GetExtrinsicResponse(
            block_number=BlockNumber(1000),
            extrinsic_index=ExtrinsicIndex(0),
            extrinsic_hash=ExtrinsicHash("0xf28cf21731dbe93b0fbb607334be06ec456f02c102084e08f19cc4d65b9b8434"),
            extrinsic_length=ExtrinsicLength(10),
            address=None,
            call=ExtrinsicCall(
                call_module="Timestamp",
                call_function="set",
                call_args=[ExtrinsicCallArg(name="now", type="Moment", value=1_764_090_180_000)],
            ),
        )
        route_mock.mock(return_value=Response(status_code=codes.OK, json=expected_response.model_dump(mode="json")))

        with pylon_client:
            response = self.make_endpoint_call(pylon_client)

        assert response == expected_response
