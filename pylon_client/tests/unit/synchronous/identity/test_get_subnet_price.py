from http import HTTPMethod

import pytest

from pylon_client._internal.pylon_commons._unstable.endpoints import Endpoint as EndpointUnstable
from pylon_client._internal.pylon_commons.currency import CurrencyRao
from pylon_client._internal.pylon_commons.types import AlphaPriceRao
from pylon_client.artanis import BlockHash, BlockNumber, NetUid, Token
from pylon_client.artanis.unstable import Block, GetPriceResponse
from tests.unit.synchronous.base_test import IdentityEndpointTest


class TestSyncIdentityGetLatestPrice(IdentityEndpointTest):
    endpoint = EndpointUnstable.SUBNET_LATEST_PRICE
    route_params = {"identity_name": "sn1", "netuid": 1}
    http_method = HTTPMethod.GET

    def make_endpoint_call(self, client):
        return client.unstable.identity.get_latest_price()

    @pytest.fixture
    def success_response(self) -> GetPriceResponse:
        return GetPriceResponse(
            block=Block(number=BlockNumber(1000), hash=BlockHash("0x123")),
            netuid=NetUid(1),
            price=AlphaPriceRao(CurrencyRao[Token.TAO](1_000_000)),
        )


class TestSyncIdentityGetPrice(IdentityEndpointTest):
    endpoint = EndpointUnstable.SUBNET_PRICE
    route_params = {"identity_name": "sn1", "netuid": 1, "block_number": 500}
    http_method = HTTPMethod.GET

    def make_endpoint_call(self, client):
        return client.unstable.identity.get_price(block_number=BlockNumber(500))

    @pytest.fixture
    def success_response(self) -> GetPriceResponse:
        return GetPriceResponse(
            block=Block(number=BlockNumber(500), hash=BlockHash("0x500")),
            netuid=NetUid(1),
            price=AlphaPriceRao(CurrencyRao[Token.TAO](7_777)),
        )
