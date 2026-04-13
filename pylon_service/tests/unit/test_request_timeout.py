import asyncio

import pytest
from litestar.status_codes import HTTP_400_BAD_REQUEST, HTTP_504_GATEWAY_TIMEOUT
from litestar.testing import AsyncTestClient

from pylon_service.middleware import request_timeout

_ENDPOINT = "/api/v1/subnet/1/block/latest/neurons"


async def _slow_response(*args, **kwargs):
    await asyncio.sleep(0.5)


@pytest.mark.asyncio
async def test_request_times_out_with_header(
    open_access_test_client: AsyncTestClient, mock_bt_client_factory, snapshot_json
):
    async with mock_bt_client_factory() as mock_client:
        async with mock_client.mock_behavior(get_latest_block=[_slow_response]):
            response = await open_access_test_client.get(_ENDPOINT, headers={"x-pylon-timeout": "0.1"})

    assert response.status_code == HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_request_times_out_with_default(
    open_access_test_client: AsyncTestClient, mock_bt_client_factory, monkeypatch, snapshot_json
):
    monkeypatch.setattr(request_timeout.settings, "default_request_timeout_seconds", 0.1)

    async with mock_bt_client_factory() as mock_client:
        async with mock_client.mock_behavior(get_latest_block=[_slow_response]):
            response = await open_access_test_client.get(_ENDPOINT)

    assert response.status_code == HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_timeout_capped_at_max(
    open_access_test_client: AsyncTestClient, mock_bt_client_factory, monkeypatch, snapshot_json
):
    monkeypatch.setattr(request_timeout.settings, "max_request_timeout_seconds", 0.1)

    async with mock_bt_client_factory() as mock_client:
        async with mock_client.mock_behavior(get_latest_block=[_slow_response]):
            response = await open_access_test_client.get(_ENDPOINT, headers={"x-pylon-timeout": "2"})

    assert response.status_code == HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == snapshot_json


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "header_value",
    [
        pytest.param("not-a-number", id="non_numeric"),
        pytest.param("-5.0", id="negative"),
        pytest.param("0", id="zero"),
    ],
)
async def test_invalid_header_returns_400(open_access_test_client: AsyncTestClient, header_value: str, snapshot_json):
    response = await open_access_test_client.get(_ENDPOINT, headers={"x-pylon-timeout": header_value})

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json() == snapshot_json
