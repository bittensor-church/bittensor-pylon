import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from httpx import Response, codes
from tenacity import stop_after_attempt

from pylon_client._internal.pylon_commons.timeout import TIMEOUT_HEADER
from pylon_client._internal.pylon_commons.v1.endpoints import Endpoint as EndpointV1
from pylon_client.artanis import (
    ASYNC_DEFAULT_RETRIES,
    DEFAULT_RETRIES,
    AsyncConfig,
    AsyncPylonClient,
    BlockHash,
    BlockNumber,
    Config,
    NetUid,
    PylonAuthToken,
    PylonClient,
    PylonTimeout,
    PylonTimeoutException,
)
from pylon_client.artanis.v1 import Block, GetNeuronsResponse

NEURONS_URL = EndpointV1.RECENT_NEURONS.absolute_url(netuid_=NetUid(1))
NEURONS_RESPONSE_JSON = GetNeuronsResponse(
    block=Block(number=BlockNumber(1), hash=BlockHash("0x1")),
    neurons={},
).model_dump(mode="json")


class _SlowHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        time.sleep(0.5)
        self.send_response(200)
        self.end_headers()


@pytest.fixture
def slow_server():
    server = HTTPServer(("127.0.0.1", 0), _SlowHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


class TestSyncClientTimeout:
    def test_sends_timeout_header(self, test_url, service_mock):
        route = service_mock.get(NEURONS_URL).mock(
            return_value=Response(status_code=codes.OK, json=NEURONS_RESPONSE_JSON)
        )
        timeout = PylonTimeout(read=120.0)
        client = PylonClient(Config(address=test_url, open_access_token=PylonAuthToken("token"), timeout=timeout))
        with client:
            client.v1.open_access.get_recent_neurons(netuid=NetUid(1))

        assert route.calls.last.request.headers[TIMEOUT_HEADER] == "120.0"

    def test_times_out_when_server_is_slow(self, slow_server):
        timeout = PylonTimeout(connect=1.0, read=0.1, write=1.0, pool=1.0)
        client = PylonClient(
            Config(
                address=slow_server,
                open_access_token=PylonAuthToken("token"),
                timeout=timeout,
                retry=DEFAULT_RETRIES.copy(stop=stop_after_attempt(1)),
            )
        )
        with client:
            with pytest.raises(PylonTimeoutException, match=r"Request to Pylon API timed out \(read\) after 0\.1s\."):
                client.v1.open_access.get_recent_neurons(netuid=NetUid(1))


class TestAsyncClientTimeout:
    @pytest.mark.asyncio
    async def test_sends_timeout_header(self, test_url, service_mock):
        route = service_mock.get(NEURONS_URL).mock(
            return_value=Response(status_code=codes.OK, json=NEURONS_RESPONSE_JSON)
        )
        timeout = PylonTimeout(read=120.0)
        client = AsyncPylonClient(
            AsyncConfig(address=test_url, open_access_token=PylonAuthToken("token"), timeout=timeout)
        )
        async with client:
            await client.v1.open_access.get_recent_neurons(netuid=NetUid(1))

        assert route.calls.last.request.headers[TIMEOUT_HEADER] == "120.0"

    @pytest.mark.asyncio
    async def test_times_out_when_server_is_slow(self, slow_server):
        timeout = PylonTimeout(connect=1.0, read=0.1, write=1.0, pool=1.0)
        client = AsyncPylonClient(
            AsyncConfig(
                address=slow_server,
                open_access_token=PylonAuthToken("token"),
                timeout=timeout,
                retry=ASYNC_DEFAULT_RETRIES.copy(stop=stop_after_attempt(1)),
            )
        )
        async with client:
            with pytest.raises(PylonTimeoutException, match=r"Request to Pylon API timed out \(read\) after 0\.1s\."):
                await client.v1.open_access.get_recent_neurons(netuid=NetUid(1))
