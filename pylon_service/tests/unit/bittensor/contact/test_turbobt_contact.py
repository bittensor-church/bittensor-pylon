import asyncio
from unittest.mock import AsyncMock, create_autospec, patch

import pytest
import pytest_asyncio
from pylon_commons.types import BlockNumber
from turbobt import BlockReference as TurboBtBlockReference
from turbobt.block import Block as TurboBtBlock
from turbobt.client import Bittensor
from pylon_commons.types import BittensorNetwork

from pylon_service.bittensor.contact import TurboBtContact


@pytest.fixture
def bittensor_ctor():
    with patch("pylon_service.bittensor.contact.Bittensor") as ctor:
        yield ctor


@pytest.fixture
def raw_client(bittensor_ctor):
    client = create_autospec(Bittensor, instance=True)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    bittensor_ctor.return_value = client
    return client


@pytest.fixture
def block_ref(raw_client):
    ref = create_autospec(TurboBtBlockReference, instance=True)
    raw_client.block.return_value = ref
    return ref


@pytest_asyncio.fixture
async def open_contact(raw_client):
    contact = TurboBtContact(wallet=None, uri=BittensorNetwork("mock://test"))
    await contact.open()
    try:
        yield contact
    finally:
        if contact._raw_client is not None:
            await contact.close()


@pytest.mark.asyncio
async def test_turbobt_contact_requires_open_before_use():
    contact = TurboBtContact(wallet=None, uri=BittensorNetwork("mock://test"))

    with pytest.raises(AttributeError, match="not open"):
        await contact.get_latest_block()


@pytest.mark.asyncio
async def test_cancelled_task_does_not_cancel_turbobt_call(open_contact, block_ref):
    turbobt_call_started = asyncio.Event()
    turbobt_call_gate = asyncio.Event()
    turbobt_call_completed = asyncio.Event()

    async def slow_get():
        turbobt_call_started.set()
        await turbobt_call_gate.wait()
        turbobt_call_completed.set()
        return TurboBtBlock("hash", 202, client=open_contact._raw_client)

    block_ref.get.side_effect = slow_get

    task = asyncio.create_task(open_contact.get_block(BlockNumber(202)))
    await turbobt_call_started.wait()

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    turbobt_call_gate.set()
    await asyncio.wait_for(turbobt_call_completed.wait(), timeout=1)
    assert turbobt_call_completed.is_set()
