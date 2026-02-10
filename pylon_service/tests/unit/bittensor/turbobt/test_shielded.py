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


@pytest.mark.asyncio
async def test_runtime_error_triggers_client_recreation_and_retry(turbobt_client, bittensor_spec, block_spec):
    call_count = 0

    async def failing_then_succeeding_get():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("turbobt internal state broken")
        return TurboBtBlock("hash", 42, client=turbobt_client._raw_client)

    block_spec.get.side_effect = failing_then_succeeding_get

    result = await turbobt_client.get_block(BlockNumber(42))

    assert result.number == 42
    assert result.hash == "hash"
    assert call_count == 2
    bittensor_spec.return_value.__aexit__.assert_called_once()
    assert bittensor_spec.call_count == 2


@pytest.mark.asyncio
async def test_runtime_error_on_retry_propagates(turbobt_client, block_spec):
    block_spec.get.side_effect = RuntimeError("turbobt broken permanently")

    with pytest.raises(RuntimeError, match="turbobt broken permanently"):
        await turbobt_client.get_block(BlockNumber(42))


@pytest.mark.asyncio
async def test_non_runtime_error_propagates_without_retry(turbobt_client, bittensor_spec, block_spec):
    block_spec.get.side_effect = ValueError("some other error")

    with pytest.raises(ValueError, match="some other error"):
        await turbobt_client.get_block(BlockNumber(42))

    bittensor_spec.return_value.__aexit__.assert_not_called()
    assert bittensor_spec.call_count == 1
