import pytest
from litestar.status_codes import HTTP_200_OK
from pylon_commons.currency import CurrencyRao, Token
from pylon_commons.models import Block, SubnetPrice
from pylon_commons.types import AlphaPriceRao, BlockHash, BlockNumber, NetUid


@pytest.mark.asyncio
async def test_unstable_identity_get_latest_price_returns_price(
    identity_test_client_factory, mock_bt_client_factory, snapshot_json
):
    block = Block(number=BlockNumber(1000), hash=BlockHash("0xlatest"))
    price = SubnetPrice(block=block, netuid=NetUid(1), price=AlphaPriceRao(CurrencyRao[Token.TAO](1_000_000)))
    async with mock_bt_client_factory("sn1") as mock_client:
        async with mock_client.mock_behavior(get_latest_block=[block], get_alpha_price=[price]):
            async with identity_test_client_factory("sn1") as client:
                response = await client.get("/api/_unstable/identity/sn1/subnet/1/block/latest/price")

    assert response.status_code == HTTP_200_OK, response.content
    assert response.json() == snapshot_json
