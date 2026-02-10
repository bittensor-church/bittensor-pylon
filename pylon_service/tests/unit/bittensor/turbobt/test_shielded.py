import asyncio
from unittest.mock import create_autospec

import pytest
from pylon_commons.models import Block
from pylon_commons.types import BittensorNetwork, BlockHash, BlockNumber
from turbobt import Bittensor
from turbobt import BlockReference as TurboBtBlockReference
from turbobt.block import Block as TurboBtBlock

from pylon_service.bittensor.client import TurboBtClient


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
    old_bittensor_mock = bittensor_spec.return_value

    block_spec.get.side_effect = RuntimeError("turbobt internal state broken")

    new_bittensor_mock = create_autospec(Bittensor, instance=True)
    new_bittensor_mock.__aenter__.return_value = new_bittensor_mock

    new_block_spec = create_autospec(TurboBtBlockReference, instance=True)
    new_block_spec.get.return_value = TurboBtBlock("hash", 42, client=new_bittensor_mock)
    new_bittensor_mock.block.return_value = new_block_spec

    bittensor_spec.return_value = new_bittensor_mock

    result = await turbobt_client.get_block(BlockNumber(42))

    assert result == Block(number=BlockNumber(42), hash=BlockHash("hash"))
    assert block_spec.get.call_count == 1
    assert new_block_spec.get.call_count == 1
    old_bittensor_mock.__aexit__.assert_called_once()
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


@pytest.mark.asyncio
async def test_get_bt_client_waits_for_event(turbobt_client):
    turbobt_client._is_client_ready.clear()

    task = asyncio.create_task(turbobt_client._get_bt_client())
    await asyncio.sleep(0)
    assert not task.done()

    turbobt_client._is_client_ready.set()
    result = await asyncio.wait_for(task, timeout=1)
    assert result is turbobt_client._raw_client


@pytest.mark.asyncio
async def test_recreate_deduplicates_concurrent_calls(turbobt_client, bittensor_spec):
    exit_gate = asyncio.Event()
    exit_call_count = 0

    async def slow_first_exit(*args):
        nonlocal exit_call_count
        exit_call_count += 1
        if exit_call_count == 1:
            await exit_gate.wait()

    bittensor_spec.return_value.__aexit__.side_effect = slow_first_exit
    bittensor_spec.reset_mock()

    task1 = asyncio.create_task(turbobt_client._recreate_bt_client())
    await asyncio.sleep(0)

    task2 = asyncio.create_task(turbobt_client._recreate_bt_client())
    await asyncio.sleep(0)
    assert not task1.done()
    assert not task2.done()

    exit_gate.set()
    await asyncio.wait_for(asyncio.gather(task1, task2), timeout=1)

    assert bittensor_spec.call_count == 1


@pytest.mark.asyncio
async def test_open_sets_event(monkeypatch, bittensor_spec, wallet):
    monkeypatch.setattr("pylon_service.bittensor.client.Bittensor", bittensor_spec)
    client = TurboBtClient(wallet=wallet, uri=BittensorNetwork("ws://testserver"))
    assert not client._is_client_ready.is_set()
    await client.open()
    assert client._is_client_ready.is_set()
    await client.close()


@pytest.mark.asyncio
async def test_close_clears_event(turbobt_client, bittensor_spec):
    assert turbobt_client._is_client_ready.is_set()
    await turbobt_client.close()
    assert not turbobt_client._is_client_ready.is_set()


@pytest.mark.asyncio
async def test_close_waits_for_recreation_to_finish(turbobt_client, bittensor_spec):
    exit_gate = asyncio.Event()
    exit_call_count = 0

    async def slow_first_exit(*args):
        nonlocal exit_call_count
        exit_call_count += 1
        if exit_call_count == 1:
            await exit_gate.wait()

    bittensor_spec.return_value.__aexit__.side_effect = slow_first_exit

    recreate_task = asyncio.create_task(turbobt_client._recreate_bt_client())
    await asyncio.sleep(0)

    close_task = asyncio.create_task(turbobt_client.close())
    await asyncio.sleep(0)
    assert not close_task.done()

    exit_gate.set()
    await asyncio.wait_for(asyncio.gather(recreate_task, close_task), timeout=1)

    assert not turbobt_client._is_client_ready.is_set()
    assert turbobt_client._raw_client is None


@pytest.mark.asyncio
async def test_recreate_waits_for_open_to_finish(monkeypatch, bittensor_spec, wallet):
    enter_gate = asyncio.Event()

    async def slow_aenter(*args):
        await enter_gate.wait()
        return bittensor_spec.return_value

    bittensor_spec.return_value.__aenter__.side_effect = slow_aenter

    monkeypatch.setattr("pylon_service.bittensor.client.Bittensor", bittensor_spec)
    client = TurboBtClient(wallet=wallet, uri=BittensorNetwork("ws://testserver"))

    open_task = asyncio.create_task(client.open())
    await asyncio.sleep(0)
    assert not open_task.done()
    assert client._raw_client is not None
    assert not client._is_client_ready.is_set()

    recreate_task = asyncio.create_task(client._recreate_bt_client())
    await asyncio.sleep(0)
    assert not recreate_task.done()

    enter_gate.set()
    await asyncio.wait_for(asyncio.gather(open_task, recreate_task), timeout=1)

    assert client._is_client_ready.is_set()
    assert bittensor_spec.call_count == 1
