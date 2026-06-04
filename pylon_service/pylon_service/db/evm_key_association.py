from collections.abc import Sequence

from pylon_commons.types import BlockNumber, NetUid
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from pylon_service.db.database import session_factory
from pylon_service.db.models import EvmKeyAssociation, PersistedEvmKeyAssociationPeriod


async def get_persisted_evm_key_association_periods(
    netuid: NetUid, block_from: BlockNumber, block_to: BlockNumber
) -> Sequence[PersistedEvmKeyAssociationPeriod]:
    async with session_factory() as session:
        statement = select(PersistedEvmKeyAssociationPeriod).where(
            PersistedEvmKeyAssociationPeriod.netuid == netuid,
            PersistedEvmKeyAssociationPeriod.block_from <= block_to,
            PersistedEvmKeyAssociationPeriod.block_to >= block_from,
        )
        result = await session.execute(statement)
        return result.scalars().all()


async def get_persisted_evm_key_association_period_at_block(
    session: AsyncSession, netuid: NetUid, block_number: BlockNumber
) -> PersistedEvmKeyAssociationPeriod | None:
    statement = select(PersistedEvmKeyAssociationPeriod).where(
        PersistedEvmKeyAssociationPeriod.netuid == netuid,
        PersistedEvmKeyAssociationPeriod.block_from <= block_number,
        PersistedEvmKeyAssociationPeriod.block_to >= block_number,
    )
    result = await session.execute(statement)
    return result.scalars().one_or_none()


async def get_evm_key_associations(
    netuid: NetUid, block_from: BlockNumber, block_to: BlockNumber
) -> Sequence[EvmKeyAssociation]:
    async with session_factory() as session:
        statement = select(EvmKeyAssociation).where(
            EvmKeyAssociation.netuid == netuid,
            EvmKeyAssociation.block_from <= block_to,
            EvmKeyAssociation.block_to >= block_from,
        )
        result = await session.execute(statement)
        return result.scalars().all()


async def get_evm_key_association(
    session: AsyncSession, netuid: NetUid, uid: int, block_number: BlockNumber
) -> EvmKeyAssociation | None:
    statement = select(EvmKeyAssociation).where(
        EvmKeyAssociation.netuid == netuid,
        EvmKeyAssociation.uid == uid,
        EvmKeyAssociation.block_from <= block_number,
        EvmKeyAssociation.block_to >= block_number,
    )
    result = await session.execute(statement)
    return result.scalars().one_or_none()


async def remove_outdated_associations(netuid: NetUid, block_number: BlockNumber) -> None:
    async with session_factory() as session:
        async with session.begin():
            await session.execute(
                delete(PersistedEvmKeyAssociationPeriod).where(
                    PersistedEvmKeyAssociationPeriod.netuid == netuid,
                    PersistedEvmKeyAssociationPeriod.block_to < block_number,
                )
            )
            await session.execute(
                delete(EvmKeyAssociation).where(
                    EvmKeyAssociation.netuid == netuid,
                    EvmKeyAssociation.block_to < block_number,
                )
            )
