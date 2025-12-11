import asyncio
import logging
from collections.abc import Generator
from typing import TypeVar

from tenacity import AsyncRetrying, stop_after_attempt, wait_fixed

from pylon._internal.background import AsyncioQueue, TaskProcessor
from pylon._internal.common.models import Block
from pylon._internal.common.types import NetUid, Timestamp
from pylon.service.bittensor.cache.manager import AbstractCacheManager
from pylon.service.bittensor.client import BittensorClient
from pylon.service.bittensor.pool import BittensorClientPool

logger = logging.getLogger(__name__)

queue = AsyncioQueue()
processor = TaskProcessor(queue, timeout=30)


_MAX_RETRIES = 3
_WAIT_TIME = 2
_BATCH_SIZE = 5

_Retry = AsyncRetrying(
    stop=stop_after_attempt(_MAX_RETRIES),
    wait=wait_fixed(_WAIT_TIME),
    reraise=True,
)

T = TypeVar("T")


def _chunk(data: list[T], size: int) -> Generator[list[T], None, None]:
    data = data.copy()
    for i in range(0, len(data), size):
        yield data[i : i + size]


async def _fetch_neurons_batch(
    client: BittensorClient,
    cache_manager: AbstractCacheManager,
    netuids: list[NetUid],
    block: Block,
    timestamp: Timestamp,
) -> set[NetUid]:
    tasks = (client.get_neurons(netuid, block) for netuid in netuids)
    result = await asyncio.gather(*tasks, return_exceptions=True)

    failed: set[NetUid] = set()

    for netuid, neurons in zip(netuids, result):
        if isinstance(neurons, BaseException):
            logger.warning(f"Failed to fetch neurons. netuid: {netuid}, error: {neurons}")
            failed.add(netuid)
        else:
            await cache_manager.set_recent_neurons(netuid, timestamp, block, neurons)

    return failed


@processor.register("update-recent-neurons", timeout=90)
async def update_recent_neurons(
    netuids: list[NetUid],
    cache_manager: AbstractCacheManager,
    pool: BittensorClientPool[BittensorClient],
) -> None:
    if not netuids:
        return

    logger.info(f"Starting recent neurons update for netuids: {', '.join(map(str, netuids))}")

    client: BittensorClient
    async with pool.acquire(wallet=None) as client:
        try:
            block = await _Retry.wraps(client.get_latest_block)()
        except Exception as e:
            logger.exception(f"Failed to fetch latest block. error: {e}")
            return

        try:
            timestamp = await _Retry.wraps(client.get_block_timestamp)(block)
        except Exception as e:
            logger.exception(f"Failed to fetch block timestamp. error: {e}")
            return

        netuids_to_process = netuids.copy()
        attempt = 1
        while netuids_to_process and attempt <= _MAX_RETRIES:
            failed = set()

            for batch in _chunk(netuids_to_process, _BATCH_SIZE):
                f = await _fetch_neurons_batch(client, cache_manager, batch, block, timestamp)
                failed = failed | f
                await asyncio.sleep(_WAIT_TIME)

            attempt += 1
            netuids_to_process = list(failed)

        total = len(netuids)
        failed = len(netuids_to_process)
        succeeded = total - failed

        logger.info(f"Finished recent neurons update. total: {total}, succeeded: {succeeded}, failed: {failed}")
        if failed:
            logger.error(f"Failed to fetch recent neurons for netuids: {', '.join(map(str, netuids_to_process))}")
