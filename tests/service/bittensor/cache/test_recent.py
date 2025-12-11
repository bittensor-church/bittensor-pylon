"""
Tests for recent data provider.
"""

import datetime as dt

import pytest

from pylon._internal.common.models import SubnetNeurons
from pylon._internal.common.types import NetUid, Timestamp
from pylon.service.bittensor.cache.models import CacheEntry
from pylon.service.bittensor.cache.recent import BittensorCacheError, RecentDataConfig, RecentDataProvider
from tests.behave import Behave
from tests.mock_cache_manager import MockCacheManager


@pytest.fixture
def provider(mock_bt_cache_manager):
    config = RecentDataConfig(recent_neurons_soft_limit=10, recent_neurons_hard_limit=20)
    return RecentDataProvider(config, mock_bt_cache_manager)


@pytest.mark.asyncio
async def test_get_recent_neurons_no_data(provider, behave: Behave, mock_bt_cache_manager: MockCacheManager):
    async with behave.mock(get_recent_neurons=[None]):
        with pytest.raises(BittensorCacheError, match="Recent neurons not found. netuid: 1"):
            await provider.get_recent_neurons(NetUid(1))
    assert behave.calls["get_recent_neurons"] == [(NetUid(1),)]


@pytest.mark.asyncio
async def test_get_recent_neurons_stale(
    provider,
    recent_neurons_factory,
    behave: Behave,
    mock_bt_cache_manager: MockCacheManager,
):
    _, block, subnet_neurons = recent_neurons_factory()
    now = dt.datetime.now().timestamp()
    timestamp = Timestamp(int(now) - 300)
    entry = CacheEntry[SubnetNeurons](cached_at=timestamp, block=block, entry=subnet_neurons)
    async with behave.mock(get_recent_neurons=[entry]):
        with pytest.raises(BittensorCacheError, match="Recent neurons cache is stale. netuid: 1"):
            await provider.get_recent_neurons(NetUid(1))
    assert behave.calls["get_recent_neurons"] == [(NetUid(1),)]


@pytest.mark.asyncio
async def test_get_recent_neurons_old(
    provider,
    recent_neurons_factory,
    caplog,
    behave: Behave,
    mock_bt_cache_manager: MockCacheManager,
):
    _, block, subnet_neurons = recent_neurons_factory()
    now = dt.datetime.now().timestamp()
    timestamp = Timestamp(int(now) - 150)
    entry = CacheEntry[SubnetNeurons](cached_at=timestamp, block=block, entry=subnet_neurons)
    async with behave.mock(get_recent_neurons=[entry]):
        result = await provider.get_recent_neurons(NetUid(1))

    assert behave.calls["get_recent_neurons"] == [(NetUid(1),)]
    assert result == subnet_neurons
    assert caplog.messages[-1] == (
        "Recent neurons cache is older than soft limit. netuid: 1, elapsed blocks: 12, hard_limit: 20"
    )


@pytest.mark.asyncio
async def test_get_recent_neurons(
    provider,
    recent_neurons_factory,
    caplog,
    behave: Behave,
    mock_bt_cache_manager: MockCacheManager,
):
    _, block, subnet_neurons = recent_neurons_factory()
    now = dt.datetime.now().timestamp()
    timestamp = Timestamp(int(now) - 10)
    entry = CacheEntry[SubnetNeurons](cached_at=timestamp, block=block, entry=subnet_neurons)
    async with behave.mock(get_recent_neurons=[entry]):
        result = await provider.get_recent_neurons(NetUid(1))

    assert behave.calls["get_recent_neurons"] == [(NetUid(1),)]
    assert result == subnet_neurons
