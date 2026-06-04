import asyncio
import logging
from collections import defaultdict

from pylon_commons.types import BlockNumber, EvmAddress, Hotkey, NetUid
from tenacity import AsyncRetrying, stop_before_delay, wait_exponential

from pylon_service.bittensor.contact_router import BittensorContactRouter
from pylon_service.bittensor.evm_keys.utils import UniqueMaxPriorityQueue
from pylon_service.bittensor.pool import BittensorContactPool
from pylon_service.db.database import session_factory
from pylon_service.db.evm_key_association import (
    get_evm_key_association,
    get_persisted_evm_key_association_period_at_block,
    get_persisted_evm_key_association_periods,
    remove_outdated_associations,
)
from pylon_service.db.models import EvmKeyAssociation, PersistedEvmKeyAssociationPeriod

logger = logging.getLogger(__name__)


class UpdateEvmKeyAssociations:
    def __init__(self, pool: BittensorContactPool, persistence_retention_blocks: int):
        self._pool = pool
        self._persistence_retention_blocks = persistence_retention_blocks

    async def execute(self, netuid: NetUid):
        async with self._pool.acquire(wallet=None) as client:
            latest_block = await client.get_latest_block()
            block_number_to = latest_block.number
            block_number_from = BlockNumber(max(1, block_number_to - self._persistence_retention_blocks + 1))
            await remove_outdated_associations(netuid, block_number_from)
            missing_periods = await self._get_missing_periods(netuid, block_number_from, block_number_to)
            for block_from, block_to in missing_periods:
                await self._update_evm_key_associations_for_period(client, netuid, block_from, block_to)
        logger.info(f"Evm key associations updated for netuid: {netuid}, periods: {missing_periods}")

    async def _get_missing_periods(
        self, netuid: NetUid, block_number_from: BlockNumber, block_number_to: BlockNumber
    ) -> list[tuple[BlockNumber, BlockNumber]]:
        persisted_periods = await get_persisted_evm_key_association_periods(netuid, block_number_from, block_number_to)

        if not persisted_periods:
            return [(block_number_from, block_number_to)]

        sorted_periods = sorted(persisted_periods, key=lambda period: period.block_from)
        missing_periods = []
        if sorted_periods[0].block_from > block_number_from:
            missing_periods.append((block_number_from, sorted_periods[0].block_from - 1))
        for i in range(len(sorted_periods) - 1):
            if sorted_periods[i + 1].block_from > sorted_periods[i].block_to + 1:
                missing_periods.append((sorted_periods[i].block_to + 1, sorted_periods[i + 1].block_from - 1))
        if sorted_periods[-1].block_to < block_number_to:
            missing_periods.append((sorted_periods[-1].block_to + 1, block_number_to))
        return missing_periods

    async def _update_evm_key_associations_for_period(
        self, client: BittensorContactRouter, netuid: NetUid, block_from: BlockNumber, block_to: BlockNumber
    ) -> None:
        blocks_to_process = UniqueMaxPriorityQueue()
        blocks_to_process.add(block_to)
        earliest_correctly_processed_block: BlockNumber | None = None
        known_associations: defaultdict[int, list[tuple[BlockNumber, Hotkey, EvmAddress, BlockNumber]]] = defaultdict(
            list
        )
        registrations: defaultdict[int, set[BlockNumber]] = defaultdict(set)
        fully_processed = False
        try:
            while not blocks_to_process.is_empty():
                block_number = BlockNumber(blocks_to_process.pop_max())
                block = await client.get_block(block_number)
                if block is None:
                    raise RuntimeError(f"Block {block_number} not found.")
                state = await client.get_subnet_state(netuid, block)
                if state is None:
                    raise RuntimeError(f"Subnet state is unavailable for netuid {netuid} at block {block_number}.")

                for uid in range(len(state.hotkeys)):
                    block_at_registration = state.block_at_registration[uid]
                    if block_at_registration > block_from:
                        # possible association for previous neuron registered under the same uid
                        blocks_to_process.add(block_at_registration - 1)
                        registrations[uid].add(block_at_registration)

                raw_associations = await client.get_evm_key_associations(netuid, block)
                for uid, association_info in raw_associations.items():
                    hotkey = Hotkey(state.hotkeys[uid])
                    last_block_where_ownership_was_proven = association_info.last_block_where_ownership_was_proven
                    known_associations[uid].append(
                        (
                            block_from,
                            hotkey,
                            association_info.evm_address,
                            association_info.last_block_where_ownership_was_proven,
                        )
                    )
                    if last_block_where_ownership_was_proven > block_from:
                        # possible another association earlier in the period
                        blocks_to_process.add(last_block_where_ownership_was_proven - 1)

                earliest_correctly_processed_block = block_number

            fully_processed = True
        finally:
            # persist correctly the processed part even if the whole period was not fully processed due to some error
            processed_block_from = block_from if fully_processed else earliest_correctly_processed_block
            if processed_block_from is not None:
                await self._save_associations(netuid, processed_block_from, block_to, known_associations, registrations)

    async def _save_associations(
        self,
        netuid: NetUid,
        period_block_from: BlockNumber,
        period_block_to: BlockNumber,
        known_associations: dict[
            int, list[tuple[BlockNumber, Hotkey, EvmAddress, BlockNumber]]
        ],  # (block_from, hotkey, evm_address, block_at_ownership_proof)
        registrations: defaultdict[int, set[BlockNumber]],
    ) -> None:
        async with session_factory() as session:
            async with session.begin():
                following_persisted_period = await get_persisted_evm_key_association_period_at_block(
                    session, netuid, BlockNumber(period_block_to + 1)
                )
                if following_persisted_period and following_persisted_period.block_from == period_block_to + 1:
                    persisted_period = following_persisted_period
                    persisted_period.block_from = period_block_from
                else:
                    persisted_period = PersistedEvmKeyAssociationPeriod(
                        netuid=netuid,
                        block_from=period_block_from,
                        block_to=period_block_to,
                    )
                    session.add(persisted_period)

                preceding_persisted_period = await get_persisted_evm_key_association_period_at_block(
                    session, netuid, BlockNumber(period_block_from - 1)
                )
                if preceding_persisted_period and preceding_persisted_period.block_to == period_block_from - 1:
                    persisted_period.block_from = preceding_persisted_period.block_from
                    await session.delete(preceding_persisted_period)

                for uid in known_associations:
                    following_association = await get_evm_key_association(
                        session, netuid, uid, BlockNumber(period_block_to + 1)
                    )
                    for block_from, hotkey, evm_address, block_at_ownership_proof in known_associations[uid]:
                        block_to = min(
                            [
                                period_block_to if not following_association else following_association.block_from - 1,
                                *[b - 1 for b in registrations[uid] if b > block_from],
                            ]
                        )
                        if (
                            following_association
                            and following_association.block_from == block_to + 1
                            and following_association.matches(hotkey, evm_address, block_at_ownership_proof)
                        ):
                            following_association.block_from = block_from
                        else:
                            following_association = EvmKeyAssociation(
                                netuid=netuid,
                                uid=uid,
                                block_from=block_from,
                                block_to=block_to,
                                hotkey=hotkey,
                                evm_address=evm_address,
                                block_at_ownership_proof=block_at_ownership_proof,
                            )
                            session.add(following_association)

                    preceding_association = await get_evm_key_association(
                        session, netuid, uid, BlockNumber(period_block_from - 1)
                    )
                    if (
                        preceding_association
                        and following_association
                        and preceding_association.block_to == following_association.block_from - 1
                        and preceding_association.matches_association(following_association)
                    ):
                        following_association.block_from = preceding_association.block_from
                        await session.delete(preceding_association)


class EvmKeyAssociationsUpdateTaskExecutor:
    def __init__(self, updater: UpdateEvmKeyAssociations, netuids: set[NetUid], timeout: float):
        self._updater = updater
        self._netuids = netuids
        self._timeout = timeout

        retry_timeout_margin = 10
        retry_deadline = max(timeout - retry_timeout_margin, 0)
        self._retrying = AsyncRetrying(
            wait=wait_exponential(multiplier=10, min=10, max=120),
            stop=stop_before_delay(retry_deadline),
            reraise=True,
        )

    async def run(self) -> None:
        # FIXME launching task per netuid complicates cleaning up outdated associations (currently done per netuid)
        tasks = [self.task(netuid) for netuid in self._netuids]
        try:
            async with asyncio.timeout(self._timeout):
                results = await asyncio.gather(*tasks, return_exceptions=True)
        except TimeoutError:
            logger.exception("Timeout while waiting for UpdateEvmKeyAssociations tasks to complete.")
            return

        for netuid, result in zip(self._netuids, results):
            if isinstance(result, BaseException):
                logger.exception(f"Failed to update evm key associations,  netuid: {netuid}, error: {result}")

    async def task(self, netuid: NetUid) -> None:
        await self._retrying.wraps(self._updater.execute)(netuid)
