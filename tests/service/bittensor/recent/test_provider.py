import datetime as dt

import pytest

from pylon_client._internal.common.constants import BLOCK_PROCESSING_TIME
from pylon_client._internal.common.models import BittensorModel
from pylon_client._internal.common.types import HotkeyName, NetUid, Timestamp
from pylon_client.service.bittensor.recent import (
    HardLimit,
    IdentitySubnetContext,
    RecentObjectMissing,
    RecentObjectProvider,
    RecentObjectStale,
    SoftLimit,
)
from pylon_client.service.bittensor.recent.adapter import CacheKey, _CacheEntry


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
def recent_object_provider(mock_recent_objects_store, wallet) -> RecentObjectProvider:
    return RecentObjectProvider(
        soft_limit=SoftLimit(2),
        hard_limit=HardLimit(4),
        store=mock_recent_objects_store,
        context=IdentitySubnetContext(NetUid(1), wallet),
    )


@pytest.mark.asyncio
async def test_get_missing(mock_recent_objects_store, recent_object_provider, cache_key):
    async with mock_recent_objects_store.behave.mock(get=[None]):
        with pytest.raises(RecentObjectMissing):
            await recent_object_provider.get(AnObjectModel)

    assert mock_recent_objects_store.behave.calls["get"] == [(cache_key, None)]


@pytest.mark.asyncio
async def test_get_stale(mock_recent_objects_store, recent_object_provider, object_, cache_key):
    timestamp = Timestamp(int(dt.datetime.now().timestamp()) - BLOCK_PROCESSING_TIME * 5)
    cache_entry = _CacheEntry(data=object_.model_dump_json(), timestamp=timestamp)
    async with mock_recent_objects_store.behave.mock(get=[cache_entry.model_dump_json().encode()]):
        with pytest.raises(RecentObjectStale):
            await recent_object_provider.get(AnObjectModel)

    assert mock_recent_objects_store.behave.calls["get"] == [(cache_key, None)]


@pytest.mark.asyncio
async def test_get_success(mock_recent_objects_store, recent_object_provider, object_, cache_key):
    timestamp = Timestamp(int(dt.datetime.now().timestamp()))
    cache_entry = _CacheEntry(data=object_.model_dump_json(), timestamp=timestamp)
    async with mock_recent_objects_store.behave.mock(get=[cache_entry.model_dump_json().encode()]):
        result = await recent_object_provider.get(AnObjectModel)
        assert result == object_

    assert mock_recent_objects_store.behave.calls["get"] == [(cache_key, None)]
