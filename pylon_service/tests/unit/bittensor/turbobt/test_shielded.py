import asyncio

import pytest
from pylon_commons.types import BlockNumber
from turbobt.block import Block as TurboBtBlock


@pytest.mark.asyncio
async def test_cancelled_task_does_not_cancel_turbobt_call(turbobt_client, block_spec):
    turbobt_call_started = asyncio.Event()
    turbobt_call_gate = asyncio.Event()
    turbobt_call_completed = asyncio.Event()

    async def slow_get():
        turbobt_call_started.set()
        await turbobt_call_gate.wait()
        turbobt_call_completed.set()
        return TurboBtBlock("hash", 202, client=turbobt_client._raw_client)

    block_spec.get.side_effect = slow_get

    task = asyncio.create_task(turbobt_client.get_block(BlockNumber(202)))
    await turbobt_call_started.wait()

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    turbobt_call_gate.set()
    await asyncio.wait_for(turbobt_call_completed.wait(), timeout=1)
    assert turbobt_call_completed.is_set()
