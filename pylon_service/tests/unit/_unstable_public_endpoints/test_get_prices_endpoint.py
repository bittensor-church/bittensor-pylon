import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from pylon_commons.currency import CurrencyRao, Token
from pylon_commons.models import Block, SubnetPrices
from pylon_commons.types import AlphaPriceRao, BlockHash, BlockNumber, NetUid


@pytest.mark.asyncio
async def test_unstable_public_get_latest_prices_returns_all_subnets(
    test_client, mock_bt_client_factory, snapshot_json
):
    block = Block(number=BlockNumber(1000), hash=BlockHash("0xlatest"))
    prices = SubnetPrices(
        block=block,
        prices={
            NetUid(1): AlphaPriceRao(CurrencyRao[Token.TAO](1_000_000)),
            NetUid(2): AlphaPriceRao(CurrencyRao[Token.TAO](2_500_000)),
        },
    )
    async with mock_bt_client_factory() as mock_client:
        async with mock_client.mock_behavior(get_latest_block=[block], get_alpha_prices=[prices]):
            response = await test_client.get("/api/_unstable/block/latest/prices")

    assert response.status_code == HTTP_200_OK, response.content
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_unstable_public_get_prices_at_block_returns_mixed_subnets(
    test_client, mock_bt_client_factory, snapshot_json
):
    """
    A price set spanning multiple subnets (including a zero price) is returned intact.
    """
    block = Block(number=BlockNumber(500), hash=BlockHash("0xblock500"))
    prices = SubnetPrices(
        block=block,
        prices={
            NetUid(1): AlphaPriceRao(CurrencyRao[Token.TAO](1_000_000)),
            NetUid(2): AlphaPriceRao(CurrencyRao[Token.TAO](0)),
            NetUid(7): AlphaPriceRao(CurrencyRao[Token.TAO](9_999)),
        },
    )
    async with mock_bt_client_factory() as mock_client:
        async with mock_client.mock_behavior(get_block=[block], get_alpha_prices=[prices]):
            response = await test_client.get("/api/_unstable/block/500/prices")

    assert response.status_code == HTTP_200_OK, response.content
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_unstable_public_get_prices_block_not_found_returns_404(
    test_client, mock_bt_client_factory, snapshot_json
):
    async with mock_bt_client_factory() as mock_client:
        async with mock_client.mock_behavior(get_block=[None]):
            response = await test_client.get("/api/_unstable/block/999999999/prices")

    assert response.status_code == HTTP_404_NOT_FOUND, response.content
    assert response.json() == snapshot_json
