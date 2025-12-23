import datetime as dt

import pytest

from pylon._internal.common.constants import BLOCK_PROCESSING_TIME
from pylon._internal.common.models import BittensorModel
from pylon._internal.common.types import NetUid, Timestamp
from pylon.service.bittensor.cache.recent import (
    RecentCacheAdapter,
    RecentDataMissing,
    RecentDataProvider,
    RecentDataStale,
    _RecentCacheEntry,
)


class AnObjectModel(BittensorModel):
    field_1: str
    field_2: int


@pytest.fixture
def object_() -> AnObjectModel:
    return AnObjectModel(field_1="test", field_2=123)


@pytest.fixture
def cache_adapter(mock_store) -> RecentCacheAdapter[AnObjectModel]:
    return RecentCacheAdapter[AnObjectModel](store=mock_store, model=AnObjectModel)


@pytest.fixture
def recent_data_provider(mock_store) -> RecentDataProvider:
    return RecentDataProvider(2, 4, mock_store)


@pytest.mark.asyncio
async def test_get_missing(behave, recent_data_provider, cache_adapter):
    async with behave.mock(get=[None]):
        with pytest.raises(RecentDataMissing):
            await recent_data_provider._get(NetUid(1), cache_adapter)

    assert behave.calls["get"] == [("recent_AnObjectModel_1", None)]


@pytest.mark.asyncio
async def test_get_stale(behave, recent_data_provider, cache_adapter, object_):
    timestamp = Timestamp(int(dt.datetime.now().timestamp()) - BLOCK_PROCESSING_TIME * 5)
    cache_entry = _RecentCacheEntry[AnObjectModel](entry=object_, timestamp=timestamp)
    async with behave.mock(get=[cache_entry.model_dump_json().encode()]):
        with pytest.raises(RecentDataStale):
            await recent_data_provider._get(NetUid(1), cache_adapter)

    assert behave.calls["get"] == [("recent_AnObjectModel_1", None)]


@pytest.mark.asyncio
async def test_get_success(behave, recent_data_provider, cache_adapter, object_):
    timestamp = Timestamp(int(dt.datetime.now().timestamp()))
    cache_entry = _RecentCacheEntry[AnObjectModel](entry=object_, timestamp=timestamp)
    async with behave.mock(get=[cache_entry.model_dump_json().encode()]):
        result = await recent_data_provider._get(NetUid(1), cache_adapter)
        assert result == object_

    assert behave.calls["get"] == [("recent_AnObjectModel_1", None)]
