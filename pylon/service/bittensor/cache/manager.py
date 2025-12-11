from abc import ABC, abstractmethod

from litestar.stores.base import Store

from pylon._internal.common.models import Block, SubnetNeurons
from pylon._internal.common.types import NetUid, Timestamp
from pylon.service.bittensor.cache.models import CacheEntry


class AbstractCacheManager(ABC):
    @abstractmethod
    async def get_recent_neurons(self, netuid: NetUid) -> CacheEntry[SubnetNeurons] | None:
        pass

    @abstractmethod
    async def set_recent_neurons(
        self,
        netuid: NetUid,
        timestamp: Timestamp,
        block: Block,
        neurons: SubnetNeurons,
    ) -> None:
        pass


class BittensorCacheManager(AbstractCacheManager):
    def __init__(self, store: Store) -> None:
        self._store = store

    @classmethod
    def _get_recent_neurons_cache_key(cls, netuid: NetUid) -> str:
        return f"{netuid}_recent_neurons"

    async def get_recent_neurons(self, netuid: NetUid) -> CacheEntry[SubnetNeurons] | None:
        cache_key = self._get_recent_neurons_cache_key(netuid)
        data = await self._store.get(cache_key)
        return CacheEntry[SubnetNeurons].model_validate_json(data) if data else None

    async def set_recent_neurons(
        self,
        netuid: NetUid,
        timestamp: Timestamp,
        block: Block,
        neurons: SubnetNeurons,
    ) -> None:
        cache_key = self._get_recent_neurons_cache_key(netuid)
        entry: CacheEntry[SubnetNeurons] = CacheEntry(entry=neurons, block=block, cached_at=timestamp)
        data = entry.model_dump_json()
        await self._store.set(cache_key, data)
