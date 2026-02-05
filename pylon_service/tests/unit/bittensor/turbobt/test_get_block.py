import pytest
from pylon_commons.models import Block
from pylon_commons.types import BlockHash, BlockNumber
from turbobt.block import Block as TurboBtBlock


@pytest.mark.asyncio
async def test_turbobt_client_get_block(turbobt_client, block_spec):
    block_spec.get.return_value = TurboBtBlock("hash", 202, client=turbobt_client._raw_client)
    result = await turbobt_client.get_block(BlockNumber(202))
    assert result == Block(hash=BlockHash("hash"), number=BlockNumber(202))


@pytest.mark.asyncio
async def test_turbobt_client_get_block_returns_none_when_hash_is_none(turbobt_client, block_spec):
    block_spec.get.return_value = TurboBtBlock(None, 202, client=turbobt_client._raw_client)  # type: ignore[arg-type]
    result = await turbobt_client.get_block(BlockNumber(202))
    assert result is None


@pytest.mark.asyncio
async def test_turbobt_client_get_block_returns_none_when_number_is_none(turbobt_client, block_spec):
    block_spec.get.return_value = TurboBtBlock("hash", None, client=turbobt_client._raw_client)
    result = await turbobt_client.get_block(BlockNumber(202))
    assert result is None


@pytest.mark.asyncio
async def test_turbobt_client_get_block_returns_none_when_block_is_none(turbobt_client, block_spec):
    block_spec.get.return_value = None
    result = await turbobt_client.get_block(BlockNumber(202))
    assert result is None
