import asyncio

import pytest
from litestar.status_codes import HTTP_400_BAD_REQUEST, HTTP_504_GATEWAY_TIMEOUT
from litestar.testing import AsyncTestClient

from pylon_service.middleware import request_timeout
from tests.mock_bittensor_client import MockBittensorClient

_ENDPOINT = "/api/v1/subnet/1/block/latest/neurons"


async def _slow_response(*args, **kwargs):
    await asyncio.sleep(0.5)


@pytest.mark.asyncio
async def test_request_times_out_with_header(
    test_client: AsyncTestClient, open_access_mock_bt_client: MockBittensorClient
):
    async with open_access_mock_bt_client.mock_behavior(get_latest_block=[_slow_response]):
        response = await test_client.get(_ENDPOINT, headers={"x-pylon-timeout": "0.1"})

    assert response.status_code == HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == {
        "status_code": HTTP_504_GATEWAY_TIMEOUT,
        "detail": "Request timed out",
    }


@pytest.mark.asyncio
async def test_request_times_out_with_default(
    test_client: AsyncTestClient, open_access_mock_bt_client: MockBittensorClient, monkeypatch
):
    monkeypatch.setattr(request_timeout.settings, "default_request_timeout_seconds", 0.1)

    async with open_access_mock_bt_client.mock_behavior(get_latest_block=[_slow_response]):
        response = await test_client.get(_ENDPOINT)

    assert response.status_code == HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == {
        "status_code": HTTP_504_GATEWAY_TIMEOUT,
        "detail": "Request timed out",
    }


@pytest.mark.asyncio
async def test_timeout_capped_at_max(
    test_client: AsyncTestClient, open_access_mock_bt_client: MockBittensorClient, monkeypatch
):
    monkeypatch.setattr(request_timeout.settings, "max_request_timeout_seconds", 0.1)

    async with open_access_mock_bt_client.mock_behavior(get_latest_block=[_slow_response]):
        response = await test_client.get(_ENDPOINT, headers={"x-pylon-timeout": "2"})

    assert response.status_code == HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == {
        "status_code": HTTP_504_GATEWAY_TIMEOUT,
        "detail": "Request timed out",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("header_value", "expected_detail"),
    [
        pytest.param("not-a-number", "Invalid X-Pylon-Timeout header value: not-a-number", id="non_numeric"),
        pytest.param("-5.0", "X-Pylon-Timeout header value must be positive, got -5.0", id="negative"),
        pytest.param("0", "X-Pylon-Timeout header value must be positive, got 0.0", id="zero"),
    ],
)
async def test_invalid_header_returns_400(test_client: AsyncTestClient, header_value: str, expected_detail: str):
    response = await test_client.get(_ENDPOINT, headers={"x-pylon-timeout": header_value})

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json() == {
        "status_code": HTTP_400_BAD_REQUEST,
        "detail": expected_detail,
    }
