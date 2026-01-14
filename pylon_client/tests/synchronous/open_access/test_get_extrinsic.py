from http import HTTPMethod

import pytest
from httpx import Response, codes
from pydantic import ValidationError

from pylon_client._internal.pylon_commons.endpoints import Endpoint
from pylon_client._internal.pylon_commons.models import ExtrinsicCall
from pylon_client._internal.pylon_commons.requests import GetExtrinsicRequest
from pylon_client._internal.pylon_commons.responses import GetExtrinsicResponse
from pylon_client._internal.pylon_commons.types import BlockNumber, ExtrinsicHash, ExtrinsicIndex, ExtrinsicLength
from tests.synchronous.base_test import OpenAccessEndpointTest


class TestSyncOpenAccessGetExtrinsic(OpenAccessEndpointTest):
    endpoint = Endpoint.EXTRINSIC
    route_params = {"block_number": 1000, "extrinsic_index": 0}
    http_method = HTTPMethod.GET

    def make_endpoint_call(self, client):
        return client.open_access.get_extrinsic(block_number=BlockNumber(1000), extrinsic_index=ExtrinsicIndex(0))

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
                    {"name": "dest", "type": "AccountId", "value": "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"},
                    {"name": "value", "type": "Balance", "value": 1000000000},
                ],
            ),
        )

    def test_unsigned_extrinsic(self, pylon_client, service_mock, route_mock):
        """
        Test getting an unsigned extrinsic (address is None).
        """
        expected_response = GetExtrinsicResponse(
            block_number=BlockNumber(1000),
            extrinsic_index=ExtrinsicIndex(0),
            extrinsic_hash=ExtrinsicHash("0xf28cf21731dbe93b0fbb607334be06ec456f02c102084e08f19cc4d65b9b8434"),
            extrinsic_length=ExtrinsicLength(10),
            address=None,
            call=ExtrinsicCall(
                call_module="Timestamp",
                call_function="set",
                call_args=[{"name": "now", "type": "Moment", "value": 1764090180000}],
            ),
        )
        route_mock.mock(return_value=Response(status_code=codes.OK, json=expected_response.model_dump(mode="json")))

        with pylon_client:
            response = self.make_endpoint_call(pylon_client)

        assert response == expected_response


@pytest.mark.parametrize(
    "invalid_block_number,expected_errors",
    [
        pytest.param(
            "not_a_number",
            [
                {
                    "type": "int_parsing",
                    "loc": ("block_number",),
                    "msg": "Input should be a valid integer, unable to parse string as an integer",
                },
            ],
            id="string_value",
        ),
        pytest.param(
            123.456,
            [
                {
                    "type": "int_from_float",
                    "loc": ("block_number",),
                    "msg": "Input should be a valid integer, got a number with a fractional part",
                },
            ],
            id="float_value",
        ),
        pytest.param(
            [123],
            [
                {"type": "int_type", "loc": ("block_number",), "msg": "Input should be a valid integer"},
            ],
            id="list_value",
        ),
        pytest.param(
            {"block": 123},
            [
                {"type": "int_type", "loc": ("block_number",), "msg": "Input should be a valid integer"},
            ],
            id="dict_value",
        ),
    ],
)
def test_sync_get_extrinsic_request_block_number_validation_error(invalid_block_number, expected_errors):
    """
    Test that GetExtrinsicRequest validates block_number type correctly.
    """
    with pytest.raises(ValidationError) as exc_info:
        GetExtrinsicRequest(block_number=invalid_block_number, extrinsic_index=ExtrinsicIndex(0))

    errors = exc_info.value.errors(include_url=False, include_context=False, include_input=False)
    assert errors == expected_errors


@pytest.mark.parametrize(
    "invalid_extrinsic_index,expected_errors",
    [
        pytest.param(
            "not_a_number",
            [
                {
                    "type": "int_parsing",
                    "loc": ("extrinsic_index",),
                    "msg": "Input should be a valid integer, unable to parse string as an integer",
                },
            ],
            id="string_value",
        ),
        pytest.param(
            123.456,
            [
                {
                    "type": "int_from_float",
                    "loc": ("extrinsic_index",),
                    "msg": "Input should be a valid integer, got a number with a fractional part",
                },
            ],
            id="float_value",
        ),
        pytest.param(
            [123],
            [
                {"type": "int_type", "loc": ("extrinsic_index",), "msg": "Input should be a valid integer"},
            ],
            id="list_value",
        ),
        pytest.param(
            {"index": 123},
            [
                {"type": "int_type", "loc": ("extrinsic_index",), "msg": "Input should be a valid integer"},
            ],
            id="dict_value",
        ),
    ],
)
def test_sync_get_extrinsic_request_extrinsic_index_validation_error(invalid_extrinsic_index, expected_errors):
    """
    Test that GetExtrinsicRequest validates extrinsic_index type correctly.
    """
    with pytest.raises(ValidationError) as exc_info:
        GetExtrinsicRequest(block_number=BlockNumber(1000), extrinsic_index=invalid_extrinsic_index)

    errors = exc_info.value.errors(include_url=False, include_context=False, include_input=False)
    assert errors == expected_errors
