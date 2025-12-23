import datetime as dt

import pytest

from pylon_client._internal.common.constants import BLOCK_PROCESSING_TIME
from pylon_client._internal.common.models import BittensorModel
from pylon_client._internal.common.types import HotkeyName, NetUid, Timestamp
from pylon_client.service.bittensor.cache.recent import RecentObjectMissing, RecentObjectProvider, RecentObjectStale
from pylon_client.service.bittensor.cache.recent.adapter import CacheKey, _CacheEntry
from pylon_client.service.bittensor.cache.recent.scope import IdentitySubnetScope
from pylon_client.service.stores import StoreName


class AnObjectModel(BittensorModel):
    field_1: str
    field_2: int


@pytest.fixture
def cache_key(wallet) -> CacheKey:
    return CacheKey(AnObjectModel, NetUid(1), HotkeyName(wallet.hotkey_str))


@pytest.fixture
def object_() -> AnObjectModel:
    return AnObjectModel(field_1="test", field_2=123)


@pytest.fixture
def recent_object_provider(mock_stores, wallet) -> RecentObjectProvider:
    return RecentObjectProvider(
        soft_limit=2,
        hard_limit=4,
        store=mock_stores[StoreName.RECENT_OBJECTS],
        scope=IdentitySubnetScope(NetUid(1), wallet),
    )


@pytest.mark.asyncio
async def test_get_missing(behave, recent_object_provider, cache_key):
    async with behave.mock(get=[None]):
        with pytest.raises(RecentObjectMissing):
            await recent_object_provider.get(AnObjectModel)

    assert behave.calls["get"] == [(cache_key, None)]


@pytest.mark.asyncio
async def test_get_stale(behave, recent_object_provider, object_, cache_key):
    timestamp = Timestamp(int(dt.datetime.now().timestamp()) - BLOCK_PROCESSING_TIME * 5)
    cache_entry = _CacheEntry(data=object_.model_dump_json(), timestamp=timestamp)
    async with behave.mock(get=[cache_entry.model_dump_json().encode()]):
        with pytest.raises(RecentObjectStale):
            await recent_object_provider.get(AnObjectModel)

    assert behave.calls["get"] == [(cache_key, None)]


@pytest.mark.asyncio
async def test_get_success(behave, recent_object_provider, object_, cache_key):
    timestamp = Timestamp(int(dt.datetime.now().timestamp()))
    cache_entry = _CacheEntry(data=object_.model_dump_json(), timestamp=timestamp)
    async with behave.mock(get=[cache_entry.model_dump_json().encode()]):
        result = await recent_object_provider.get(AnObjectModel)
        assert result == object_

    assert behave.calls["get"] == [(cache_key, None)]
