import pytest

from pylon_client._internal.common.models import Block, SubnetCommitments
from pylon_client._internal.common.types import BlockHash, BlockNumber, CommitmentDataHex, Hotkey


@pytest.fixture
def test_block():
    return Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))


@pytest.fixture
def subnet_spec(subnet_spec):
    subnet_spec.commitments.fetch.return_value = {
        "hotkey1": bytes.fromhex("deadbeef"),
        "hotkey2": bytes.fromhex("cafebabe"),
    }
    return subnet_spec


@pytest.mark.asyncio
async def test_turbobt_client_get_commitments(turbobt_client, subnet_spec, test_block):
    """
    Test that get_commitments returns all commitments for a subnet.
    """
    result = await turbobt_client.get_commitments(netuid=1, block=test_block)
    assert result == SubnetCommitments(
        block=test_block,
        commitments={
            Hotkey("hotkey1"): CommitmentDataHex("0xdeadbeef"),
            Hotkey("hotkey2"): CommitmentDataHex("0xcafebabe"),
        },
    )
    subnet_spec.commitments.fetch.assert_called_once_with(block_hash=test_block.hash)


@pytest.mark.asyncio
async def test_turbobt_client_get_commitments_empty(turbobt_client, subnet_spec, test_block):
    """
    Test that get_commitments returns empty dict when no commitments exist.
    """
    subnet_spec.commitments.fetch.return_value = {}
    result = await turbobt_client.get_commitments(netuid=1, block=test_block)
    assert result == SubnetCommitments(
        block=test_block,
        commitments={},
    )
