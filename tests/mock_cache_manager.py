from pylon._internal.common.models import Block, SubnetNeurons
from pylon._internal.common.types import NetUid, Timestamp
from pylon.service.bittensor.cache.manager import AbstractCacheManager
from pylon.service.bittensor.cache.models import CacheEntry
from tests.behave import Behave


class MockCacheManager(AbstractCacheManager):
    def __init__(self, behave: Behave) -> None:
        self._behave = behave

    async def get_recent_neurons(self, netuid: NetUid) -> CacheEntry[SubnetNeurons] | None:
        self._behave.track("get_recent_neurons", netuid)
        return await self._behave.execute("get_recent_neurons", netuid)

    async def set_recent_neurons(
        self, netuid: NetUid, timestamp: Timestamp, block: Block, neurons: SubnetNeurons
    ) -> None:
        self._behave.track("set_recent_neurons", netuid, timestamp, block, neurons)
        return await self._behave.execute("set_recent_neurons", netuid, timestamp, block, neurons)
