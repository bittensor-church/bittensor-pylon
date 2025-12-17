import datetime as dt
import logging
from typing import Generic, TypeVar

from litestar.stores.base import Store
from pydantic import BaseModel

from pylon._internal.common.constants import BLOCK_PROCESSING_TIME
from pylon._internal.common.models import BittensorModel, SubnetNeurons
from pylon._internal.common.types import NetUid, Timestamp
from pylon.service.bittensor.cache.exceptions import BittensorCacheException

logger = logging.getLogger(__name__)


T = TypeVar("T", bound=BittensorModel)


class _RecentCacheEntry(BaseModel, Generic[T]):
    """
    A cache entry class internal to this module. It is a generic class that represents a single
    cached 'entry' along with the corresponding block's timestamp.
    """

    entry: T
    timestamp: Timestamp


class RecentCacheAdapter(Generic[T]):
    """
    A generic cache adapter on top of the litestar store. It is responsible for serializing/deserializing
    and getting/saving objects as recent entries.

    This class works on a single object type level and takes the object model type as a parameter.
    This model is used to deserialize the objects to correct types.
    """

    def __init__(
        self,
        store: Store,
        model: type[T],
    ) -> None:
        """
        Args:
            store: a litestar store instance to store and retrieve cache entries.
            model: a BittensorModel class to deserialize cache entries to correct types.
        """
        self.model = model
        self._store = store

    def _build_cache_key(self, netuid: NetUid) -> str:
        return f"recent_{self.model.__name__}_{netuid}"

    async def save(self, netuid: NetUid, timestamp: Timestamp, object_: T) -> None:
        """
        Saves a cache entry to the underlying store.
        Args:
            netuid: netuid of the subnet the object belongs to.
            timestamp: timestamp of the block this data is associated with.
            object_: The object to be cached.
        """
        cache_key = self._build_cache_key(netuid)
        entry = _RecentCacheEntry(entry=object_, timestamp=timestamp)
        data = entry.model_dump_json()
        await self._store.set(cache_key, data)

    async def get(self, netuid: NetUid) -> _RecentCacheEntry[T] | None:
        """
        Gets a cache entry from the store backend.
        Args:
            netuid: netuid of the subnet the object belongs to.
        """
        cache_key = self._build_cache_key(netuid)
        data = await self._store.get(cache_key)
        if data is None:
            return None

        # self._model is needed here for deserializing entry to a correct object.
        cache_entry = _RecentCacheEntry[self.model].model_validate_json(data)
        return cache_entry


class RecentDataMissing(BittensorCacheException):
    """
    Raised when recent data is missing for an object from the cache.
    """


class RecentDataStale(BittensorCacheException):
    """
    Raised when recent data is stale (w.r.t hard limit) for an object from the cache.
    """


class RecentDataProvider:
    """
    A readonly facade for accessing recent data objects from the cache. It performs freshness checks on
    recent objects and raises exceptions if they are stale or missing.
    """

    def __init__(self, soft_limit: int, hard_limit: int, store: Store) -> None:
        """
        Args:
            store: a litestar store instance. It is directly passed to cache adapters for accessing recent data.
            soft_limit: soft limit for recent data age in blocks. Logs warnings if data is older than this limit.
            hard_limit: hard limit for recent data age in blocks. Raises exceptions if data is older than this limit.
        """
        self._soft_limit = soft_limit
        self._hard_limit = hard_limit
        self._store = store

    async def _get(self, netuid: NetUid, cache_adapter: RecentCacheAdapter[T]) -> T:
        """
        This is a private method that gets a recent object from the cache. It performs freshness checks on the object.
        Based on the freshness checks, it either raises an exception or returns the object.
        Args:
            netuid:
            cache_adapter:

        Raises:
            RecentDataMissing: if the object is missing from the cache.
            RecentDataStale: if the object is stale (older than hard limit).
        """
        object_name = cache_adapter.model.__name__

        cache_entry = await cache_adapter.get(netuid)
        if cache_entry is None:
            raise RecentDataMissing(f"Recent data not found. netuid: {netuid}, object: {object_name}")

        cached_at = cache_entry.timestamp
        now = dt.datetime.now(tz=dt.UTC).timestamp()
        elapsed_blocks = int(max(0, int(now - cached_at)) / BLOCK_PROCESSING_TIME)

        if elapsed_blocks > self._hard_limit:
            raise RecentDataStale(
                f"Recent data is stale. netuid: {netuid}, object: {object_name}, elapsed_blocks: {elapsed_blocks}, "
                f"hard_limit: {self._hard_limit}"
            )

        if elapsed_blocks > self._soft_limit:
            logger.warning(
                f"Recent data is older than soft limit. netuid: {netuid}, object: {object_name}, "
                f"elapsed blocks: {elapsed_blocks}, soft_limit: {self._soft_limit}"
            )

        return cache_entry.entry

    async def get_recent_neurons(self, netuid: NetUid) -> SubnetNeurons:
        """
        Get recent neurons for a subnet.
        Args:
            netuid: subnet netuid
        """
        recent_object = RecentCacheAdapter[SubnetNeurons](self._store, SubnetNeurons)
        return await self._get(netuid, recent_object)
