"""
Tests for HTTP error handling in the sync communicator.
"""

import pytest
from httpx import ConnectTimeout, PoolTimeout, ReadTimeout, Response, TimeoutException, WriteTimeout, codes

from pylon_client._internal.pylon_commons.apiver import ApiVersion
from pylon_client._internal.pylon_commons.endpoints import Endpoint
from pylon_client._internal.pylon_commons.exceptions import (
    PylonBadGateway,
    PylonForbidden,
    PylonNotFound,
    PylonResponseException,
    PylonTimeoutException,
    PylonUnauthorized,
    TimeoutReason,
)
from pylon_client._internal.pylon_commons.types import BlockNumber, NetUid
from pylon_client._internal.sync.client import PylonClient


@pytest.fixture
def neurons_url():
    """
    URL for the neurons endpoint used in error handling tests.
    """
    return Endpoint.NEURONS.absolute_url(ApiVersion.V1, netuid_=NetUid(1), block_number=1000)


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
            PylonBadGateway,
            r"Bad gateway \(HTTP 502\)",
            id="bad_gateway_502",
        ),
        pytest.param(
            codes.GATEWAY_TIMEOUT,
            PylonTimeoutException,
            r"Request to Pylon API timed out \(gateway_timeout\)",
            id="gateway_timeout_504",
        ),
    ],
)
def test_status_code_raises_correct_exception(
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


@pytest.mark.parametrize(
    "status_code,expected_exception",
    [
        pytest.param(codes.UNAUTHORIZED, PylonUnauthorized, id="unauthorized_401"),
        pytest.param(codes.FORBIDDEN, PylonForbidden, id="forbidden_403"),
        pytest.param(codes.NOT_FOUND, PylonNotFound, id="not_found_404"),
        pytest.param(codes.INTERNAL_SERVER_ERROR, PylonResponseException, id="internal_server_error_500"),
        pytest.param(codes.BAD_GATEWAY, PylonBadGateway, id="bad_gateway_502"),
        pytest.param(codes.GATEWAY_TIMEOUT, PylonTimeoutException, id="gateway_timeout_504"),
    ],
)
def test_extracts_detail_from_json_response(
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
    service_mock.get(neurons_url).mock(return_value=Response(status_code=status_code, json={"detail": error_detail}))

    with sync_open_access_client:
        with pytest.raises(expected_exception) as exc_info:
            sync_open_access_client.open_access.get_neurons(netuid=NetUid(1), block_number=BlockNumber(1000))

    assert exc_info.value.detail == error_detail
    assert error_detail in str(exc_info.value)


def test_handles_json_without_detail_field(
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


@pytest.mark.parametrize(
    "httpx_exception,expected_reason,expected_timeout_seconds,expected_message",
    [
        pytest.param(
            ConnectTimeout("connect timeout"),
            TimeoutReason.CONNECT,
            5.0,
            r"Request to Pylon API timed out \(connect\) after 5\.0s\.",
            id="connect_timeout",
        ),
        pytest.param(
            ReadTimeout("read timeout"),
            TimeoutReason.READ,
            60.0,
            r"Request to Pylon API timed out \(read\) after 60\.0s\.",
            id="read_timeout",
        ),
        pytest.param(
            WriteTimeout("write timeout"),
            TimeoutReason.WRITE,
            5.0,
            r"Request to Pylon API timed out \(write\) after 5\.0s\.",
            id="write_timeout",
        ),
        pytest.param(
            PoolTimeout("pool timeout"),
            TimeoutReason.POOL,
            5.0,
            r"Request to Pylon API timed out \(pool\) after 5\.0s\.",
            id="pool_timeout",
        ),
    ],
)
def test_timeout_exception_maps_to_correct_reason(
    sync_open_access_client: PylonClient,
    service_mock,
    neurons_url,
    httpx_exception,
    expected_reason,
    expected_timeout_seconds,
    expected_message,
):
    service_mock.get(neurons_url).mock(side_effect=httpx_exception)

    with sync_open_access_client:
        with pytest.raises(PylonTimeoutException, match=expected_message) as exc_info:
            sync_open_access_client.open_access.get_neurons(netuid=NetUid(1), block_number=BlockNumber(1000))

    assert exc_info.value.reason == expected_reason
    assert exc_info.value.timeout_seconds == expected_timeout_seconds


def test_unexpected_timeout_exception_raises_type_error(
    sync_open_access_client: PylonClient,
    service_mock,
    neurons_url,
):
    service_mock.get(neurons_url).mock(side_effect=TimeoutException("unexpected"))

    with sync_open_access_client:
        with pytest.raises(TypeError, match="Unexpected timeout exception type: TimeoutException"):
            sync_open_access_client.open_access.get_neurons(netuid=NetUid(1), block_number=BlockNumber(1000))
