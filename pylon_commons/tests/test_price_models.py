from pylon_commons._unstable.endpoints import Endpoint
from pylon_commons._unstable.requests import (
    GetLatestPriceRequest,
    GetLatestPricesRequest,
    GetPriceRequest,
    GetPricesRequest,
)
from pylon_commons._unstable.responses import GetPriceResponse, GetPricesResponse
from pylon_commons.currency import CurrencyRao, Token
from pylon_commons.models import Block, SubnetPrice, SubnetPrices
from pylon_commons.types import AlphaPriceRao, BlockHash, BlockNumber, NetUid


def _block() -> Block:
    return Block(number=BlockNumber(100), hash=BlockHash("0xabc"))


def test_subnet_prices_serializes_prices_as_int():
    """
    SubnetPrices serializes its rao prices as plain ints keyed by netuid.
    """
    model = SubnetPrices(
        block=_block(),
        prices={
            NetUid(1): AlphaPriceRao(CurrencyRao[Token.TAO](123)),
            NetUid(2): AlphaPriceRao(CurrencyRao[Token.TAO](456)),
        },
    )
    assert model.model_dump(mode="json") == {
        "block": {"number": 100, "hash": "0xabc"},
        "prices": {"1": 123, "2": 456},
    }


def test_subnet_price_serializes_price_as_int():
    """
    SubnetPrice serializes a single rao price as a plain int.
    """
    model = SubnetPrice(
        block=_block(),
        netuid=NetUid(1),
        price=AlphaPriceRao(CurrencyRao[Token.TAO](789)),
    )
    assert model.model_dump(mode="json") == {
        "block": {"number": 100, "hash": "0xabc"},
        "netuid": 1,
        "price": 789,
    }


def test_price_responses_validate_from_models():
    """
    Response classes accept the corresponding model instances via from_attributes.
    """
    prices = SubnetPrices(
        block=_block(),
        prices={NetUid(1): AlphaPriceRao(CurrencyRao[Token.TAO](123))},
    )
    price = SubnetPrice(
        block=_block(),
        netuid=NetUid(1),
        price=AlphaPriceRao(CurrencyRao[Token.TAO](789)),
    )
    assert GetPricesResponse.model_validate(prices, from_attributes=True).prices == prices.prices
    assert GetPriceResponse.model_validate(price, from_attributes=True).price == price.price


def test_price_endpoints_paths_and_methods():
    """
    The four price endpoints expose the expected method, path and reverse name.
    """
    assert Endpoint.LATEST_PRICES.value == ("GET", "/block/latest/prices", "latest_prices")
    assert Endpoint.PRICES.value == ("GET", "/block/{block_number:int}/prices", "prices")
    assert Endpoint.SUBNET_LATEST_PRICE.value == ("GET", "/block/latest/price", "subnet_latest_price")
    assert Endpoint.SUBNET_PRICE.value == ("GET", "/block/{block_number:int}/price", "subnet_price")


def test_price_requests_response_classes():
    """
    Each request maps to the right response and request_type.
    """
    assert GetLatestPricesRequest.response_cls is GetPricesResponse
    assert GetPricesRequest.response_cls is GetPricesResponse
    assert GetLatestPriceRequest.response_cls is GetPriceResponse
    assert GetPriceRequest.response_cls is GetPriceResponse
    assert GetLatestPricesRequest().request_type == "get_latest_prices"
    assert GetPricesRequest(block_number=BlockNumber(1)).request_type == "get_prices"
    assert GetPriceRequest(netuid=NetUid(1), block_number=BlockNumber(1)).request_type == "get_price"
    assert GetLatestPriceRequest(netuid=NetUid(1)).request_type == "get_latest_price"
