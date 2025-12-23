import pytest

from pylon_client._internal.common.models import Block, Commitment
from pylon_client._internal.common.types import BlockHash, BlockNumber, CommitmentDataHex, Hotkey


@pytest.fixture
def test_block():
    return Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))


@pytest.fixture
def subnet_spec(subnet_spec):
    commitment_bytes = bytes.fromhex("deadbeef")
    subnet_spec.commitments.get.return_value = commitment_bytes
    return subnet_spec


@pytest.mark.asyncio
async def test_turbobt_client_get_commitment(turbobt_client, subnet_spec, test_block):
    """
    Test that get_commitment returns commitment data for a specific hotkey.
    """
    hotkey = Hotkey("test_hotkey")
    result = await turbobt_client.get_commitment(netuid=1, block=test_block, hotkey=hotkey)
    assert result == Commitment(
        block=test_block,
        hotkey=hotkey,
        commitment=CommitmentDataHex("0xdeadbeef"),
    )
    subnet_spec.commitments.get.assert_called_once_with(hotkey, block_hash=test_block.hash)


@pytest.mark.asyncio
async def test_turbobt_client_get_commitment_not_found(turbobt_client, subnet_spec, test_block):
    """
    Test that get_commitment returns None when commitment is not found.
    """
    subnet_spec.commitments.get.return_value = None
    hotkey = Hotkey("test_hotkey")
    result = await turbobt_client.get_commitment(netuid=1, block=test_block, hotkey=hotkey)
    assert result is None
