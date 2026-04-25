from pydantic import BaseModel
from pylon_commons.types import BlockNumber, NetUid, Tempo


class Epoch(BaseModel):
    start: BlockNumber
    end: BlockNumber


def get_epoch_containing_block(block: BlockNumber, netuid: NetUid, tempo: Tempo) -> Epoch:
    """
    Reimplementing the logic from subtensor's Rust function:
        pub fn blocks_until_next_epoch(netuid: u16, tempo: u16, block: u64) -> u64
    See https://github.com/opentensor/subtensor.
    See also: https://github.com/opentensor/bittensor/pull/2168/commits/9e8745447394669c03d9445373920f251630b6b8

    The beginning of an epoch is the first block when values like "dividends" are different
    (before an epoch they are constant for a full tempo).
    """
    assert tempo > 0

    interval = tempo + 1
    next_epoch = block + tempo - (block + netuid + 1) % interval

    if next_epoch == block:
        prev_epoch = next_epoch
        next_epoch = prev_epoch + interval
    else:
        prev_epoch = next_epoch - interval

    return Epoch(start=BlockNumber(prev_epoch), end=BlockNumber(next_epoch))
