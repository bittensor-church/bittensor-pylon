"""
Tests for HTTP error handling in the sync communicator.
"""

import pytest
from httpx import Response, codes

from pylon_client._internal.client.sync.client import PylonClient
from pylon_client._internal.common.endpoints import Endpoint
from pylon_client._internal.common.exceptions import (
    PylonForbidden,
    PylonNotFound,
    PylonResponseException,
    PylonUnauthorized,
)
from pylon_client._internal.common.types import BlockNumber, NetUid
from pylon_client.service.main import app


class TestHttpStatusCodeErrors:
    """
    Tests that specific HTTP status codes raise the correct exceptions.
    """

    @pytest.fixture
    def neurons_url(self):
        return app.route_reverse(Endpoint.NEURONS.reverse, netuid=1, block_number=1000)

    @pytest.mark.parametrize(
        "status_code,expected_exception,expected_message",
        [
            pytest.param(
                codes.UNAUTHORIZED,
                PylonUnauthorized,
                r"Unauthorized \(HTTP 401\)",
                id="unauthorized_401",
            ),
            pytest.param(
                codes.FORBIDDEN,
                PylonForbidden,
                r"Forbidden \(HTTP 403\)",
                id="forbidden_403",
            ),
            pytest.param(
                codes.NOT_FOUND,
                PylonNotFound,
                r"Not found \(HTTP 404\)",
                id="not_found_404",
            ),
            pytest.param(
                codes.INTERNAL_SERVER_ERROR,
                PylonResponseException,
                r"Invalid response from Pylon API \(HTTP 500\)",
                id="internal_server_error_500",
            ),
            pytest.param(
                codes.BAD_GATEWAY,
                PylonResponseException,
                r"Invalid response from Pylon API \(HTTP 502\)",
                id="bad_gateway_502",
            ),
        ],
    )
    def test_status_code_raises_correct_exception(
        self,
        sync_open_access_client: PylonClient,
        service_mock,
        neurons_url,
        status_code,
        expected_exception,
        expected_message,
    ):
        """
        Test that HTTP status codes raise the correct exception types.
        """
        service_mock.get(neurons_url).mock(return_value=Response(status_code=status_code))

        with sync_open_access_client:
            with pytest.raises(expected_exception, match=expected_message):
                sync_open_access_client.open_access.get_neurons(netuid=NetUid(1), block_number=BlockNumber(1000))


class TestErrorDetailExtraction:
    """
    Tests for extracting error details from HTTP error responses.
    """

    @pytest.fixture
    def neurons_url(self):
        return app.route_reverse(Endpoint.NEURONS.reverse, netuid=1, block_number=1000)

    @pytest.mark.parametrize(
        "status_code,expected_exception",
        [
            pytest.param(codes.UNAUTHORIZED, PylonUnauthorized, id="unauthorized_401"),
            pytest.param(codes.FORBIDDEN, PylonForbidden, id="forbidden_403"),
            pytest.param(codes.NOT_FOUND, PylonNotFound, id="not_found_404"),
            pytest.param(codes.INTERNAL_SERVER_ERROR, PylonResponseException, id="internal_server_error_500"),
        ],
    )
    def test_extracts_detail_from_json_response(
        self,
        sync_open_access_client: PylonClient,
        service_mock,
        neurons_url,
        status_code,
        expected_exception,
    ):
        """
        Test that error detail is extracted from JSON response body.
        """
        error_detail = "Resource not available"
        service_mock.get(neurons_url).mock(
            return_value=Response(status_code=status_code, json={"detail": error_detail})
        )

        with sync_open_access_client:
            with pytest.raises(expected_exception) as exc_info:
                sync_open_access_client.open_access.get_neurons(netuid=NetUid(1), block_number=BlockNumber(1000))

        assert exc_info.value.detail == error_detail
        assert error_detail in str(exc_info.value)

    def test_handles_json_without_detail_field(
        self,
        sync_open_access_client: PylonClient,
        service_mock,
        neurons_url,
    ):
        """
        Test that missing detail field in JSON response results in None detail.
        """
        service_mock.get(neurons_url).mock(
            return_value=Response(status_code=codes.NOT_FOUND, json={"error": "something else"})
        )

        with sync_open_access_client:
            with pytest.raises(PylonNotFound) as exc_info:
                sync_open_access_client.open_access.get_neurons(netuid=NetUid(1), block_number=BlockNumber(1000))

        assert exc_info.value.detail is None

    def test_handles_non_json_response(
        self,
        sync_open_access_client: PylonClient,
        service_mock,
        neurons_url,
    ):
        """
        Test that non-JSON response body results in None detail.
        """
        service_mock.get(neurons_url).mock(return_value=Response(status_code=codes.NOT_FOUND, content=b"Not Found"))

        with sync_open_access_client:
            with pytest.raises(PylonNotFound) as exc_info:
                sync_open_access_client.open_access.get_neurons(netuid=NetUid(1), block_number=BlockNumber(1000))

        assert exc_info.value.detail is None
