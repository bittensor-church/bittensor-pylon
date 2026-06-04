import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient
from pylon_commons.currency import CurrencyRao, Token
from pylon_commons.models import Block, SubnetPrice, SubnetPriceEntry
from pylon_commons.types import AlphaPriceRao, BlockHash, BlockNumber, NetUid


@pytest.mark.asyncio
async def test_unstable_open_access_get_latest_price_returns_price(
    open_access_test_client: AsyncTestClient, mock_bt_client_factory, snapshot_json
):
    block = Block(number=BlockNumber(1000), hash=BlockHash("0xlatest"))
    price = SubnetPrice(
        block=block, netuid=NetUid(1), price=SubnetPriceEntry(value=AlphaPriceRao(CurrencyRao[Token.TAO](1_000_000)))
    )
    async with mock_bt_client_factory() as mock_client:
        async with mock_client.mock_behavior(get_latest_block=[block], get_alpha_price=[price]):
            response = await open_access_test_client.get("/api/_unstable/openaccess/subnet/1/block/latest/price")

    assert response.status_code == HTTP_200_OK, response.content
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_unstable_open_access_get_price_at_block_returns_price(
    open_access_test_client: AsyncTestClient, mock_bt_client_factory, snapshot_json
):
    block = Block(number=BlockNumber(500), hash=BlockHash("0xblock500"))
    price = SubnetPrice(
        block=block, netuid=NetUid(1), price=SubnetPriceEntry(value=AlphaPriceRao(CurrencyRao[Token.TAO](7_777)))
    )
    async with mock_bt_client_factory() as mock_client:
        async with mock_client.mock_behavior(get_block=[block], get_alpha_price=[price]):
            response = await open_access_test_client.get("/api/_unstable/openaccess/subnet/1/block/500/price")

            assert response.status_code == HTTP_200_OK, response.content
            assert response.json() == snapshot_json

        assert mock_client.calls["get_alpha_price"] == [(NetUid(1), block)]


@pytest.mark.asyncio
async def test_unstable_open_access_get_price_block_not_found_returns_404(
    open_access_test_client: AsyncTestClient, mock_bt_client_factory, snapshot_json
):
    async with mock_bt_client_factory() as mock_client:
        async with mock_client.mock_behavior(get_block=[None]):
            response = await open_access_test_client.get("/api/_unstable/openaccess/subnet/1/block/999999999/price")

    assert response.status_code == HTTP_404_NOT_FOUND, response.content
    assert response.json() == snapshot_json
