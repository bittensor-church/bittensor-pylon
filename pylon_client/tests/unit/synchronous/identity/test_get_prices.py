from http import HTTPMethod

import pytest

from pylon_client._internal.pylon_commons._unstable.endpoints import Endpoint as EndpointUnstable
from pylon_client._internal.pylon_commons.currency import CurrencyRao
from pylon_client._internal.pylon_commons.types import AlphaPriceRao
from pylon_client.artanis import BlockHash, BlockNumber, NetUid, Token
from pylon_client.artanis.unstable import Block, GetPricesResponse
from tests.unit.synchronous.base_test import IdentityEndpointTest


class TestSyncIdentityGetLatestPrices(IdentityEndpointTest):
    endpoint = EndpointUnstable.LATEST_PRICES
    route_params = {}
    http_method = HTTPMethod.GET

    def make_endpoint_call(self, client):
        return client.unstable.identity.get_latest_prices()

    @pytest.fixture
    def success_response(self) -> GetPricesResponse:
        return GetPricesResponse(
            block=Block(number=BlockNumber(1000), hash=BlockHash("0x123")),
            prices={
                NetUid(1): AlphaPriceRao(CurrencyRao[Token.TAO](1_000_000)),
                NetUid(2): AlphaPriceRao(CurrencyRao[Token.TAO](2_000_000)),
            },
        )


class TestSyncIdentityGetPrices(IdentityEndpointTest):
    endpoint = EndpointUnstable.PRICES
    route_params = {"block_number": 500}
    http_method = HTTPMethod.GET

    def make_endpoint_call(self, client):
        return client.unstable.identity.get_prices(block_number=BlockNumber(500))

    @pytest.fixture
    def success_response(self) -> GetPricesResponse:
        return GetPricesResponse(
            block=Block(number=BlockNumber(500), hash=BlockHash("0x500")),
            prices={NetUid(1): AlphaPriceRao(CurrencyRao[Token.TAO](1_000_000))},
        )
