import datetime as dt
import logging
from typing import TypeVar

from litestar.stores.base import Store

from pylon_client._internal.common.constants import BLOCK_PROCESSING_TIME
from pylon_client._internal.common.models import BittensorModel

from .adapter import RecentCacheAdapter
from .exceptions import RecentObjectMissing, RecentObjectStale
from .scope import Scope

logger = logging.getLogger(__name__)


T = TypeVar("T", bound=BittensorModel)


class RecentObjectProvider:
    """
    A readonly facade for accessing recent objects from the cache. It performs freshness
    checks on the objects and raises exceptions if they are stale or missing.
    """

    def __init__(self, soft_limit: int, hard_limit: int, store: Store, scope: Scope) -> None:
        """
        Args:
            soft_limit: soft limit for recent object age in blocks.
            hard_limit: hard limit for recent object age in blocks.
            store: litestar store instance. It is directly passed to cache adapters for accessing
                recent objects.
            scope: a Scope instance that defines the scope to build the cache key for a given model.
        """
        self._soft_limit = soft_limit
        self._hard_limit = hard_limit
        self._store = store
        self._scope = scope

    async def get(self, model: type[T]) -> T:
        """
        Get a recent object from the cache. It performs freshness checks on the object.
        Based on the freshness checks, it either raises an exception or returns the object.
        Args:
            model: BittensorModel class to deserialize cache entries to correct types.

        Raises:
            RecentObjectMissing: if the object is missing from the cache.
            RecentObjectStale: if the object is stale (older than hard limit).
        """
        cache_adapter = RecentCacheAdapter(self._scope.build_key(model), self._store, model)

        cache_entry = await cache_adapter.get()
        if cache_entry is None:
            raise RecentObjectMissing(f"Recent object not found. object: {model.__name__}")

        cached_at, object_ = cache_entry
        now = dt.datetime.now(tz=dt.UTC).timestamp()
        elapsed_blocks = max(0, int(now - cached_at)) // BLOCK_PROCESSING_TIME

        if elapsed_blocks > self._hard_limit:
            raise RecentObjectStale(
                f"Recent object is stale. scope: {self._scope}, object: {model.__name__}, "
                f"elapsed_blocks: {elapsed_blocks}, hard_limit: {self._hard_limit}"
            )

        if elapsed_blocks > self._soft_limit:
            logger.warning(
                f"Recent object is older than soft limit. scope: {self._scope}, object: {model.__name__},"
                f"elapsed blocks: {elapsed_blocks}, soft_limit: {self._soft_limit}"
            )

        return object_
