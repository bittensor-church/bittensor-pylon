import pytest

from pylon._internal.common.models import BittensorModel
from pylon._internal.common.types import NetUid, Timestamp
from pylon.service.bittensor.cache.recent import RecentCacheAdapter, _RecentCacheEntry


class AnObjectModel(BittensorModel):
    field_1: str
    field_2: int


@pytest.fixture
def object_() -> AnObjectModel:
    return AnObjectModel(field_1="test", field_2=123)


@pytest.fixture
def cache_adapter(mock_store) -> RecentCacheAdapter[AnObjectModel]:
    return RecentCacheAdapter[AnObjectModel](store=mock_store, model=AnObjectModel)


@pytest.mark.asyncio
async def test_save(behave, cache_adapter, object_) -> None:
    timestamp = Timestamp(123123123)
    cache_entry = _RecentCacheEntry[AnObjectModel](entry=object_, timestamp=timestamp)
    async with behave.mock(set=[None]):
        result = await cache_adapter.save(NetUid(1), timestamp, object_)
        assert result is None

    assert behave.calls["set"] == [("recent_AnObjectModel_1", cache_entry.model_dump_json(), None)]


@pytest.mark.asyncio
async def test_get_missing(behave, cache_adapter) -> None:
    async with behave.mock(get=[None]):
        result = await cache_adapter.get(NetUid(1))
        assert result is None

    assert behave.calls["get"] == [("recent_AnObjectModel_1", None)]


@pytest.mark.asyncio
async def test_get_success(behave, cache_adapter, object_) -> None:
    cache_entry = _RecentCacheEntry[AnObjectModel](entry=object_, timestamp=Timestamp(123123123))
    async with behave.mock(get=[cache_entry.model_dump_json().encode()]):
        result = await cache_adapter.get(NetUid(1))
        assert result == cache_entry

    assert behave.calls["get"] == [("recent_AnObjectModel_1", None)]
