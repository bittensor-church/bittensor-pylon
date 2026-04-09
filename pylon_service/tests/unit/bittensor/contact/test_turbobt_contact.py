import asyncio
import contextlib
import logging
from unittest.mock import AsyncMock, create_autospec, patch

import pytest
import pytest_asyncio
from pylon_commons.models import Block
from pylon_commons.types import BittensorNetwork, BlockHash, BlockNumber
from turbobt import BlockReference as TurboBtBlockReference
from turbobt.block import Block as TurboBtBlock
from turbobt.client import Bittensor
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from pylon_service.bittensor.contact import TurboBtContact
from pylon_service.bittensor.exceptions import BittensorTransportError


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
class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@contextlib.contextmanager
def capture_contact_logs():
    contact_logger = logging.getLogger("pylon_service.bittensor.contact")
    handler = _ListHandler()
    previous_level = contact_logger.level
    contact_logger.addHandler(handler)
    contact_logger.setLevel(logging.INFO)
    try:
        yield handler.records
    finally:
        contact_logger.removeHandler(handler)
        contact_logger.setLevel(previous_level)


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


@pytest.mark.asyncio
async def test_cancelled_task_preserves_cancelled_error_when_recreation_fails(open_contact, block_ref):
    turbobt_call_started = asyncio.Event()
    turbobt_call_gate = asyncio.Event()
    turbobt_call_completed = asyncio.Event()

    async def slow_get():
        turbobt_call_started.set()
        await turbobt_call_gate.wait()
        turbobt_call_completed.set()
        return TurboBtBlock("hash", 203, client=open_contact._raw_client)

    block_ref.get.side_effect = slow_get
    open_contact._recreate_bt_client = AsyncMock(side_effect=RuntimeError("recreate failed"))

    task = asyncio.create_task(open_contact.get_block(BlockNumber(203)))
    await turbobt_call_started.wait()

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    turbobt_call_gate.set()
    await asyncio.wait_for(turbobt_call_completed.wait(), timeout=1)
    assert turbobt_call_completed.is_set()
    open_contact._recreate_bt_client.assert_awaited_once()


@pytest.mark.asyncio
async def test_runtime_error_triggers_contact_recreation_and_retry_without_traceback_logs(
    open_contact, bittensor_ctor, raw_client, block_ref
):
    old_raw_client = raw_client
    block_ref.get.side_effect = RuntimeError("turbobt internal state broken")

    new_raw_client = create_autospec(Bittensor, instance=True)
    new_raw_client.__aenter__ = AsyncMock(return_value=new_raw_client)
    new_raw_client.__aexit__ = AsyncMock(return_value=None)

    new_block_ref = create_autospec(TurboBtBlockReference, instance=True)
    new_block_ref.get.return_value = TurboBtBlock("hash", 42, client=new_raw_client)
    new_raw_client.block.return_value = new_block_ref

    bittensor_ctor.side_effect = [new_raw_client]

    with capture_contact_logs() as records:
        result = await open_contact.get_block(BlockNumber(42))

    assert result == Block(number=BlockNumber(42), hash=BlockHash("hash"))
    reconnect_records = [
        record for record in records if "Recoverable transport error during get_block" in record.getMessage()
    ]
    assert len(reconnect_records) == 1
    assert reconnect_records[0].levelno == logging.INFO
    assert reconnect_records[0].exc_info is None
    assert block_ref.get.call_count == 1
    assert new_block_ref.get.call_count == 1
    old_raw_client.__aexit__.assert_called_once()
    assert bittensor_ctor.call_count == 2


@pytest.mark.asyncio
async def test_connection_closed_error_triggers_contact_recreation_and_retry(
    open_contact, bittensor_ctor, raw_client, block_ref
):
    old_raw_client = raw_client
    block_ref.get.side_effect = ConnectionClosedError(None, None, None)

    new_raw_client = create_autospec(Bittensor, instance=True)
    new_raw_client.__aenter__ = AsyncMock(return_value=new_raw_client)
    new_raw_client.__aexit__ = AsyncMock(return_value=None)

    new_block_ref = create_autospec(TurboBtBlockReference, instance=True)
    new_block_ref.get.return_value = TurboBtBlock("hash", 42, client=new_raw_client)
    new_raw_client.block.return_value = new_block_ref

    bittensor_ctor.side_effect = [new_raw_client]

    result = await open_contact.get_block(BlockNumber(42))

    assert result == Block(number=BlockNumber(42), hash=BlockHash("hash"))
    assert block_ref.get.call_count == 1
    assert new_block_ref.get.call_count == 1
    old_raw_client.__aexit__.assert_called_once()
    assert bittensor_ctor.call_count == 2


@pytest.mark.asyncio
async def test_connection_closed_ok_triggers_contact_recreation_and_retry(
    open_contact, bittensor_ctor, raw_client, block_ref
):
    old_raw_client = raw_client
    block_ref.get.side_effect = ConnectionClosedOK(None, None, None)

    new_raw_client = create_autospec(Bittensor, instance=True)
    new_raw_client.__aenter__ = AsyncMock(return_value=new_raw_client)
    new_raw_client.__aexit__ = AsyncMock(return_value=None)

    new_block_ref = create_autospec(TurboBtBlockReference, instance=True)
    new_block_ref.get.return_value = TurboBtBlock("hash", 42, client=new_raw_client)
    new_raw_client.block.return_value = new_block_ref

    bittensor_ctor.side_effect = [new_raw_client]

    result = await open_contact.get_block(BlockNumber(42))

    assert result == Block(number=BlockNumber(42), hash=BlockHash("hash"))
    assert block_ref.get.call_count == 1
    assert new_block_ref.get.call_count == 1
    old_raw_client.__aexit__.assert_called_once()
    assert bittensor_ctor.call_count == 2


@pytest.mark.asyncio
async def test_runtime_error_on_retry_raises_bittensor_transport_error(open_contact, bittensor_ctor, block_ref):
    new_raw_client = create_autospec(Bittensor, instance=True)
    new_raw_client.__aenter__ = AsyncMock(return_value=new_raw_client)
    new_raw_client.__aexit__ = AsyncMock(return_value=None)

    new_block_ref = create_autospec(TurboBtBlockReference, instance=True)
    new_block_ref.get.side_effect = RuntimeError("turbobt broken permanently")
    new_raw_client.block.return_value = new_block_ref

    bittensor_ctor.side_effect = [new_raw_client]
    block_ref.get.side_effect = RuntimeError("turbobt broken permanently")

    with pytest.raises(
        BittensorTransportError,
        match="get_block failed on mock://test: RuntimeError: turbobt broken permanently",
    ) as exc_info:
        await open_contact.get_block(BlockNumber(42))

    assert block_ref.get.call_count == 1
    assert new_block_ref.get.call_count == 1
    assert exc_info.value.operation == "get_block"
    assert exc_info.value.uri == "mock://test"
    assert exc_info.value.error_type == "RuntimeError"
    assert exc_info.value.transport_gist == "RuntimeError: turbobt broken permanently"
    assert isinstance(exc_info.value.__cause__, RuntimeError)


@pytest.mark.asyncio
async def test_non_runtime_error_propagates_without_recreation(open_contact, bittensor_ctor, raw_client, block_ref):
    block_ref.get.side_effect = ValueError("some other error")

    with pytest.raises(ValueError, match="some other error"):
        await open_contact.get_block(BlockNumber(42))

    raw_client.__aexit__.assert_not_called()
    assert bittensor_ctor.call_count == 1
