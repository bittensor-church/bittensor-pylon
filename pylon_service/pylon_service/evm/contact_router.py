from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from pylon_commons.types import ArchiveBlocksCutoff
from pylon_commons.types import evm as evm_types

from pylon_service.evm.contact import AbstractEvmContact, EvmLog
from pylon_service.metrics import evm_archive_routing_total


class EvmContactRouter:
    def __init__(
        self,
        main_contact: AbstractEvmContact,
        archive_contact: AbstractEvmContact,
        archive_blocks_cutoff: ArchiveBlocksCutoff,
    ) -> None:
        self._main = main_contact
        self._archive = archive_contact
        self._archive_blocks_cutoff = archive_blocks_cutoff

    async def open(self) -> None:
        await self._main.open()
        await self._archive.open()

    async def close(self) -> None:
        await self._main.close()
        await self._archive.close()

    async def _delegate[T](
        self,
        from_block: evm_types.BlockNumber,
        to_block: evm_types.BlockNumber,
        call: Callable[[AbstractEvmContact, evm_types.BlockNumber, evm_types.BlockNumber], Awaitable[T]],
        combine: Callable[[T, T], T],
    ) -> T:
        current_block = await self._main.get_current_block()
        cutoff = evm_types.BlockNumber(max(0, current_block - self._archive_blocks_cutoff))

        if to_block <= cutoff:
            evm_archive_routing_total.labels(reason="archive").inc()
            return await call(self._archive, from_block, to_block)
        if from_block > cutoff:
            evm_archive_routing_total.labels(reason="main").inc()
            return await call(self._main, from_block, to_block)

        evm_archive_routing_total.labels(reason="split").inc()
        archive_result, main_result = await asyncio.gather(
            call(self._archive, from_block, cutoff),
            call(self._main, evm_types.BlockNumber(cutoff + 1), to_block),
        )
        return combine(archive_result, main_result)

    async def get_logs(
        self,
        address: evm_types.Address,
        from_block: evm_types.BlockNumber,
        to_block: evm_types.BlockNumber,
        abi: list[dict[str, Any]],
    ) -> list[EvmLog]:
        return await self._delegate(
            from_block,
            to_block,
            call=lambda contact, fb, tb: contact.get_logs(address, fb, tb, abi),
            combine=lambda a, b: a + b,
        )
