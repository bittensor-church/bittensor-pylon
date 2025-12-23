import pytest

from pylon_client._internal.common.models import BittensorModel
from pylon_client._internal.common.types import HotkeyName, NetUid, Timestamp
from pylon_client.service.bittensor.cache.recent import RecentCacheAdapter
from pylon_client.service.bittensor.cache.recent.adapter import CacheKey, _CacheEntry
from pylon_client.service.stores import StoreName


class AnObjectModel(BittensorModel):
    field_1: str
    field_2: int


@pytest.fixture
def cache_key() -> CacheKey:
    return CacheKey(AnObjectModel, NetUid(1), HotkeyName("hotkey_1"))


@pytest.fixture
def object_() -> AnObjectModel:
    return AnObjectModel(field_1="test", field_2=123)


@pytest.fixture
def cache_adapter(cache_key, mock_stores) -> RecentCacheAdapter[AnObjectModel]:
    store = mock_stores[StoreName.RECENT_OBJECTS]
    return RecentCacheAdapter(key=cache_key, store=store, model=AnObjectModel)


@pytest.mark.asyncio
async def test_save(behave, cache_adapter, object_, cache_key) -> None:
    timestamp = Timestamp(123123123)
    cache_entry = _CacheEntry(data=object_.model_dump_json(), timestamp=timestamp)
    async with behave.mock(set=[None]):
        result = await cache_adapter.save(timestamp, object_)
        assert result is None

    assert behave.calls["set"] == [(cache_key, cache_entry.model_dump_json(), None)]


@pytest.mark.asyncio
async def test_get_missing(behave, cache_adapter, cache_key) -> None:
    async with behave.mock(get=[None]):
        result = await cache_adapter.get()
        assert result is None

    assert behave.calls["get"] == [(cache_key, None)]


@pytest.mark.asyncio
async def test_get_success(behave, cache_adapter, object_, cache_key) -> None:
    cache_entry = _CacheEntry(data=object_.model_dump_json(), timestamp=Timestamp(123123123))
    async with behave.mock(get=[cache_entry.model_dump_json().encode()]):
        result = await cache_adapter.get()
        assert result == (Timestamp(123123123), object_)

    assert behave.calls["get"] == [(cache_key, None)]
