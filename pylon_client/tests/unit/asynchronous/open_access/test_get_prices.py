from http import HTTPMethod

import pytest
from httpx import Response, codes

from pylon_client._internal.pylon_commons._unstable.endpoints import Endpoint as EndpointUnstable
from pylon_client._internal.pylon_commons.currency import CurrencyRao
from pylon_client._internal.pylon_commons.types import AlphaPriceRao
from pylon_client.artanis import BlockHash, BlockNumber, NetUid, Token
from pylon_client.artanis.unstable import Block, GetPricesResponse, SubnetPriceEntry, SubnetPrices
from tests.unit.asynchronous.base_test import OpenAccessEndpointTest


class TestOpenAccessGetLatestPrices(OpenAccessEndpointTest):
    endpoint = EndpointUnstable.LATEST_PRICES
    route_params = {}
    http_method = HTTPMethod.GET

    async def make_endpoint_call(self, client):
        return await client.unstable.open_access.get_latest_prices()

    @pytest.fixture
    def success_response(self) -> GetPricesResponse:
        return GetPricesResponse(
            block=Block(number=BlockNumber(1000), hash=BlockHash("0x123")),
            prices={
                NetUid(1): SubnetPriceEntry(value=AlphaPriceRao(CurrencyRao[Token.TAO](1_000_000))),
                NetUid(2): SubnetPriceEntry(value=AlphaPriceRao(CurrencyRao[Token.TAO](2_000_000))),
            },
        )

    @pytest.mark.asyncio
    async def test_returns_prices(self, pylon_client, service_mock, route_mock):
        expected = GetPricesResponse(
            block=Block(number=BlockNumber(1000), hash=BlockHash("0x123")),
            prices={
                NetUid(1): SubnetPriceEntry(value=AlphaPriceRao(CurrencyRao[Token.TAO](1_000_000))),
                NetUid(2): SubnetPriceEntry(value=AlphaPriceRao(CurrencyRao[Token.TAO](0))),
            },
        )
        route_mock.mock(return_value=Response(status_code=codes.OK, json=expected.model_dump(mode="json")))
        async with pylon_client:
            response = await self.make_endpoint_call(pylon_client)
        assert response == expected
        assert isinstance(response, SubnetPrices)


class TestOpenAccessGetPrices(OpenAccessEndpointTest):
    endpoint = EndpointUnstable.PRICES
    route_params = {"block_number": 500}
    http_method = HTTPMethod.GET

    async def make_endpoint_call(self, client):
        return await client.unstable.open_access.get_prices(block_number=BlockNumber(500))

    @pytest.fixture
    def success_response(self) -> GetPricesResponse:
        return GetPricesResponse(
            block=Block(number=BlockNumber(500), hash=BlockHash("0x500")),
            prices={NetUid(1): SubnetPriceEntry(value=AlphaPriceRao(CurrencyRao[Token.TAO](1_000_000)))},
        )
