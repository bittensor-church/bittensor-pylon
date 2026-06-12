import asyncio

import pytest
import pytest_asyncio
from bittensor_wallet import Wallet
from pylon_commons.types import HotkeyName, WalletName

from pylon_service.bittensor.contact import TurboBtContact
from pylon_service.bittensor.contact_router import BittensorContactRouter
from pylon_service.bittensor.pool import (
    BittensorContactPool,
    BittensorContactPoolInvalidState,
    WalletKey,
)
from tests.helpers import wait_until


@pytest_asyncio.fixture
async def barrier_factory():
    barriers = []

    async def _create_barrier(parties: int):
        barrier = asyncio.Barrier(parties)
        barriers.append(barrier)
        return barrier

    try:
        yield _create_barrier
    finally:
        for barrier in barriers:
            if not barrier.broken:
                await barrier.abort()


async def acquire_client(
    pool: BittensorContactPool[BittensorContactRouter], wallet: Wallet | None, barrier: asyncio.Barrier
) -> BittensorContactRouter:
    async with pool.acquire(wallet=wallet) as client:
        await barrier.wait()
    return client


@pytest.mark.asyncio
async def test_bittensor_contact_pool_proper_use(barrier_factory):
    barrier = await barrier_factory(6)
    wallets = [Wallet(), Wallet()]
    pool = BittensorContactPool(
        uri="ws://localhost:8000",
        archive_uri="ws://localhost:8001",
    )
    await pool.open()
    assert pool.state == BittensorContactPool.State.OPEN
    tasks = [asyncio.create_task(acquire_client(pool, wallets[i % 2], barrier)) for i in range(5)]
    await wait_until(lambda: barrier.n_waiting == barrier.parties - 1)
    assert pool._acquire_counter == 5
    async with pool.acquire(wallet=wallets[0]) as client_wallet:
        assert pool._pool == {
            WalletKey(  # type: ignore[reportUnhashable]
                wallet_name=WalletName("default"), hotkey_name=HotkeyName("default"), path="~/.bittensor/wallets/"
            ): client_wallet
        }
        assert pool._acquire_counter == 6
        assert client_wallet.uri == pool.client_kwargs["uri"]
        assert client_wallet.archive_uri == pool.client_kwargs["archive_uri"]
        assert isinstance(client_wallet._main_contact, TurboBtContact)
        assert isinstance(client_wallet._archive_contact, TurboBtContact)
        assert client_wallet._main_contact._raw_client is not None
        assert client_wallet._archive_contact._raw_client is not None
    assert pool._acquire_counter == 5
    async with pool.acquire(wallet=None) as client_no_wallet:
        assert pool._pool == {
            WalletKey(  # type: ignore[reportUnhashable]
                wallet_name=WalletName("default"), hotkey_name=HotkeyName("default"), path="~/.bittensor/wallets/"
            ): client_wallet,
            None: client_no_wallet,
        }
        assert pool._acquire_counter == 6
    assert pool._acquire_counter == 5
    close_task = asyncio.create_task(pool.close())
    await wait_until(lambda: pool.state == BittensorContactPool.State.CLOSING)
    async with asyncio.timeout(2):
        await barrier.wait()
    clients = await asyncio.gather(*tasks)
    assert set(clients) == {client_wallet}
    assert pool._acquire_counter == 0
    await close_task
    assert pool.state == BittensorContactPool.State.CLOSED
    assert pool._pool == {}
    assert isinstance(client_wallet._main_contact, TurboBtContact)
    assert isinstance(client_wallet._archive_contact, TurboBtContact)
    assert client_wallet._main_contact._raw_client is None
    assert client_wallet._archive_contact._raw_client is None


@pytest.mark.asyncio
async def test_bittensor_contact_pool_acquire_when_pool_closed():
    pool = BittensorContactPool(
        uri="ws://localhost:8000",
        archive_uri="ws://localhost:8001",
    )
    with pytest.raises(BittensorContactPoolInvalidState):
        async with pool.acquire(wallet=None):
            pass


@pytest.mark.asyncio
async def test_bittensor_contact_pool_acquire_when_pool_closing(barrier_factory):
    barrier = await barrier_factory(2)
    pool = BittensorContactPool(
        uri="ws://localhost:8000",
        archive_uri="ws://localhost:8001",
    )
    await pool.open()
    task = asyncio.create_task(acquire_client(pool, None, barrier))
    await wait_until(lambda: pool._acquire_counter == 1)
    close_task = asyncio.create_task(pool.close())
    await wait_until(lambda: pool.state == BittensorContactPool.State.CLOSING)
    with pytest.raises(BittensorContactPoolInvalidState):
        async with pool.acquire(wallet=None):
            pass
    async with asyncio.timeout(2):
        await barrier.wait()
    await task
    await close_task


@pytest.mark.asyncio
async def test_bittensor_contact_pool_close_already_closed_pool():
    pool = BittensorContactPool(
        uri="ws://localhost:8000",
        archive_uri="ws://localhost:8001",
    )
    with pytest.raises(BittensorContactPoolInvalidState):
        await pool.close()


@pytest.mark.asyncio
async def test_bittensor_contact_pool_close_pool_while_closing(barrier_factory):
    barrier = await barrier_factory(2)
    pool = BittensorContactPool(
        uri="ws://localhost:8000",
        archive_uri="ws://localhost:8001",
    )
    await pool.open()
    task = asyncio.create_task(acquire_client(pool, None, barrier))
    await wait_until(lambda: pool._acquire_counter == 1)
    close_task = asyncio.create_task(pool.close())
    await wait_until(lambda: pool.state == BittensorContactPool.State.CLOSING)
    with pytest.raises(BittensorContactPoolInvalidState):
        await pool.close()
    async with asyncio.timeout(2):
        await barrier.wait()
    await task
    await close_task


@pytest.mark.asyncio
async def test_bittensor_contact_pool_close_empty_pool():
    pool = BittensorContactPool(
        uri="ws://localhost:8000",
        archive_uri="ws://localhost:8001",
    )
    await pool.open()
    assert pool.state == BittensorContactPool.State.OPEN
    await pool.close()
    assert pool.state == BittensorContactPool.State.CLOSED


@pytest.mark.asyncio
async def test_bittensor_contact_pool_stress(barrier_factory):
    barrier = await barrier_factory(10000)
    pool = BittensorContactPool(
        uri="ws://localhost:8000",
        archive_uri="ws://localhost:8001",
    )
    await pool.open()
    tasks = [asyncio.create_task(acquire_client(pool, None, barrier)) for _ in range(10000)]
    async with asyncio.timeout(3):
        clients = await asyncio.gather(*tasks)
    await pool.close()
    assert set(clients) == {clients[0]}


@pytest.mark.asyncio
async def test_bittensor_contact_pool_close_timeout(barrier_factory):
    barrier = await barrier_factory(2)
    pool = BittensorContactPool(
        pool_closing_timeout=0.1,
        uri="ws://localhost:8000",
        archive_uri="ws://localhost:8001",
    )
    await pool.open()
    task = asyncio.create_task(acquire_client(pool, None, barrier))
    await wait_until(lambda: pool._acquire_counter == 1)
    await pool.close()
    async with asyncio.timeout(2):
        await barrier.wait()
    await task
    client = task.result()
    assert isinstance(client._main_contact, TurboBtContact)
    assert isinstance(client._archive_contact, TurboBtContact)
    assert client._main_contact._raw_client is None
    assert client._archive_contact._raw_client is None
