import datetime as dt
import logging
from dataclasses import dataclass

from pylon._internal.common.constants import BLOCK_PROCESSING_TIME
from pylon._internal.common.exceptions import BasePylonException
from pylon._internal.common.models import SubnetNeurons
from pylon._internal.common.types import NetUid
from pylon.service.bittensor.cache.manager import AbstractCacheManager

logger = logging.getLogger(__name__)


class BittensorCacheError(BasePylonException):
    pass


@dataclass
class RecentDataConfig:
    recent_neurons_soft_limit: int
    recent_neurons_hard_limit: int


class RecentDataProvider:
    """
    A readonly layer on top of the cache manager that provides "recent" data from the cache.
    It performs time-based freshness checks based on the cache config and returns cached
    data or raises an exception if the cache is missing or stale.
    """

    def __init__(self, config: RecentDataConfig, manager: AbstractCacheManager):
        self._config = config
        self._manager = manager

    async def get_recent_neurons(self, netuid: NetUid) -> SubnetNeurons:
        cache_entry = await self._manager.get_recent_neurons(netuid)
        if cache_entry is None:
            raise BittensorCacheError(f"Recent neurons not found. netuid: {netuid}")

        cached_at = cache_entry.cached_at
        now = dt.datetime.now(tz=dt.UTC).timestamp()
        elapsed_blocks = int(max(0, int(now - cached_at)) / BLOCK_PROCESSING_TIME)

        if elapsed_blocks > self._config.recent_neurons_hard_limit:
            raise BittensorCacheError(
                f"Recent neurons cache is stale. netuid: {netuid}, elapsed_blocks: {elapsed_blocks}, "
                f"hard_limit: {self._config.recent_neurons_hard_limit}"
            )

        if elapsed_blocks > self._config.recent_neurons_soft_limit:
            logger.warning(
                f"Recent neurons cache is older than soft limit. netuid: {netuid}, elapsed blocks: {elapsed_blocks}, "
                f"hard_limit: {self._config.recent_neurons_hard_limit}"
            )

        return cache_entry.entry
