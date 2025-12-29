import pytest

from pylon_client._internal.common.models import BittensorModel
from pylon_client._internal.common.types import HotkeyName, NetUid, Timestamp
from pylon_client.service.bittensor.recent import RecentCacheAdapter
from pylon_client.service.bittensor.recent.adapter import CacheKey, _CacheEntry


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
def cache_adapter(cache_key, mock_recent_objects_store) -> RecentCacheAdapter[AnObjectModel]:
    return RecentCacheAdapter(key=cache_key, store=mock_recent_objects_store, model=AnObjectModel)


@pytest.mark.asyncio
async def test_save(mock_recent_objects_store, cache_adapter, object_, cache_key) -> None:
    timestamp = Timestamp(123123123)
    cache_entry = _CacheEntry(data=object_.model_dump_json(), timestamp=timestamp)
    async with mock_recent_objects_store.behave.mock(set=[None]):
        result = await cache_adapter.save(timestamp, object_)
        assert result is None

    assert mock_recent_objects_store.behave.calls["set"] == [(cache_key, cache_entry.model_dump_json(), None)]


@pytest.mark.asyncio
async def test_get_missing(mock_recent_objects_store, cache_adapter, cache_key) -> None:
    async with mock_recent_objects_store.behave.mock(get=[None]):
        result = await cache_adapter.get()
        assert result is None

    assert mock_recent_objects_store.behave.calls["get"] == [(cache_key, None)]


@pytest.mark.asyncio
async def test_get_success(mock_recent_objects_store, cache_adapter, object_, cache_key) -> None:
    cache_entry = _CacheEntry(data=object_.model_dump_json(), timestamp=Timestamp(123123123))
    async with mock_recent_objects_store.behave.mock(get=[cache_entry.model_dump_json().encode()]):
        result = await cache_adapter.get()
        assert result == (Timestamp(123123123), object_)

    assert mock_recent_objects_store.behave.calls["get"] == [(cache_key, None)]
