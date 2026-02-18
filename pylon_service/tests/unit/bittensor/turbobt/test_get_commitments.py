import pytest
from pylon_commons.models import Block, Commitment, SubnetCommitments
from pylon_commons.types import BlockHash, BlockNumber, CommitmentDataHex, Hotkey


@pytest.fixture
def test_block():
    return Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))


@pytest.fixture
def subnet_spec(subnet_spec):
    subnet_spec.commitments.fetch.return_value = {
        "hotkey1": {"data": bytes.fromhex("deadbeef"), "block": 950},
        "hotkey2": {"data": bytes.fromhex("cafebabe"), "block": 950},
    }
    subnet_spec.get_state.return_value = {
        "netuid": 1,
        "hotkeys": ["hotkey1", "hotkey2"],
        "coldkeys": ["coldkey1", "coldkey2"],
        "active": [True, True],
        "validator_permit": [False, False],
        "pruning_score": [0, 0],
        "last_update": [0, 0],
        "emission": [0, 0],
        "dividends": [0, 0],
        "incentives": [0, 0],
        "consensus": [0, 0],
        "trust": [0, 0],
        "rank": [0, 0],
        "block_at_registration": [0, 0],
        "alpha_stake": [0, 0],
        "tao_stake": [0, 0],
        "total_stake": [0, 0],
        "emission_history": [[], []],
    }
    return subnet_spec


@pytest.mark.asyncio
async def test_turbobt_client_get_commitments(turbobt_client, subnet_spec, test_block):
    """
    Test that get_commitments returns commitments for registered hotkeys in a subnet.
    """
    result = await turbobt_client.get_commitments(netuid=1, block=test_block)
    assert result == SubnetCommitments(
        block=test_block,
        commitments={
            Hotkey("hotkey1"): Commitment(
                commitment_block_number=BlockNumber(950),
                hotkey=Hotkey("hotkey1"),
                commitment=CommitmentDataHex("0xdeadbeef"),
            ),
            Hotkey("hotkey2"): Commitment(
                commitment_block_number=BlockNumber(950),
                hotkey=Hotkey("hotkey2"),
                commitment=CommitmentDataHex("0xcafebabe"),
            ),
        },
    )
    subnet_spec.commitments.fetch.assert_called_once_with(block_hash=test_block.hash)
    subnet_spec.get_state.assert_called_once_with(test_block.hash)


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


@pytest.mark.asyncio
async def test_turbobt_client_get_commitments_filters_unregistered_hotkeys(turbobt_client, subnet_spec, test_block):
    """
    Test that get_commitments filters out commitments from deregistered hotkeys.
    """
    subnet_spec.commitments.fetch.return_value = {
        "hotkey1": {"data": bytes.fromhex("deadbeef"), "block": 950},
        "hotkey2": {"data": bytes.fromhex("cafebabe"), "block": 950},
        "hotkey3": {"data": bytes.fromhex("baadf00d"), "block": 960},
    }
    result = await turbobt_client.get_commitments(netuid=1, block=test_block)
    assert result == SubnetCommitments(
        block=test_block,
        commitments={
            Hotkey("hotkey1"): Commitment(
                commitment_block_number=BlockNumber(950),
                hotkey=Hotkey("hotkey1"),
                commitment=CommitmentDataHex("0xdeadbeef"),
            ),
            Hotkey("hotkey2"): Commitment(
                commitment_block_number=BlockNumber(950),
                hotkey=Hotkey("hotkey2"),
                commitment=CommitmentDataHex("0xcafebabe"),
            ),
        },
    )
