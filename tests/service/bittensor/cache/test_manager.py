import pytest
from litestar.stores.memory import MemoryStore

from pylon._internal.common.types import NetUid
from pylon.service.bittensor.cache.manager import BittensorCacheManager


@pytest.fixture
def store():
    return MemoryStore()


@pytest.fixture
def cache_manager(store):
    return BittensorCacheManager(store)


@pytest.mark.asyncio
async def test_set_recent_neurons(store, cache_manager, recent_neurons_factory):
    await cache_manager.set_recent_neurons(NetUid(1), *recent_neurons_factory())
    result = await store.exists(cache_manager._get_recent_neurons_cache_key(NetUid(1)))
    assert result


@pytest.mark.asyncio
async def test_set_recent_neurons_override(cache_manager, recent_neurons_factory):
    netuid = NetUid(1)
    timestamp1, block1, subnet_neurons1 = recent_neurons_factory()
    timestamp2, block2, subnet_neurons2 = recent_neurons_factory()

    await cache_manager.set_recent_neurons(netuid, timestamp1, block1, subnet_neurons1)
    await cache_manager.set_recent_neurons(netuid, timestamp2, block2, subnet_neurons2)

    result = await cache_manager.get_recent_neurons(netuid)

    assert result is not None
    assert result.cached_at == timestamp2
    assert result.block == block2
    assert result.entry == subnet_neurons2


@pytest.mark.asyncio
async def test_get_recent_neurons(cache_manager, recent_neurons_factory):
    timestamp, block, subnet_neurons = recent_neurons_factory()
    await cache_manager.set_recent_neurons(NetUid(1), timestamp, block, subnet_neurons)

    result = await cache_manager.get_recent_neurons(NetUid(1))

    assert result is not None
    assert result.entry == subnet_neurons  # this is important to check serialization
    assert result.cached_at == timestamp
    assert result.block == block


@pytest.mark.asyncio
async def test_get_recent_neurons_missing(cache_manager):
    result = await cache_manager.get_recent_neurons(NetUid(1))
    assert result is None


@pytest.mark.asyncio
async def test_cache_manager_multiple_netuids(cache_manager, recent_neurons_factory):
    netuid1 = NetUid(1)
    netuid2 = NetUid(2)

    timestamp1, block1, subnet_neurons1 = recent_neurons_factory()
    timestamp2, block2, subnet_neurons2 = recent_neurons_factory()

    await cache_manager.set_recent_neurons(netuid1, timestamp1, block1, subnet_neurons1)
    await cache_manager.set_recent_neurons(netuid2, timestamp2, block2, subnet_neurons2)

    result1 = await cache_manager.get_recent_neurons(netuid1)
    result2 = await cache_manager.get_recent_neurons(netuid2)

    assert result1 is not None
    assert result2 is not None

    assert result1.entry == subnet_neurons1
    assert result2.entry == subnet_neurons2
