from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from pylon_commons.models import EvmLog
from pylon_commons.types import evm as evm_types

from pylon_service.bittensor.mock_contact import Behave
from pylon_service.evm.contact import AbstractEvmContact


class MockEvmContact(AbstractEvmContact):
    def __init__(self, rpc_url: evm_types.RpcUrl = evm_types.RpcUrl("mock://evm")):
        super().__init__(rpc_url)
        self._behave = Behave()

    async def open(self) -> None:
        pass

    async def close(self) -> None:
        pass

    @asynccontextmanager
    async def mock_behavior(self, **behaviors: list[Any] | Any):
        async with self._behave.mock(**behaviors):
            yield

    def add_behavior(self, method_name: str, behavior: Any) -> None:
        self._behave.add_behavior(method_name, behavior)

    def reset(self) -> None:
        self._behave.reset()

    @property
    def calls(self) -> dict[str, list]:
        return self._behave.calls

    async def get_current_block(self) -> evm_types.BlockNumber:
        self._behave.track("get_current_block")
        return await self._behave.execute("get_current_block")

    async def get_logs(
        self,
        address: evm_types.Address,
        from_block: evm_types.BlockNumber,
        to_block: evm_types.BlockNumber,
        abi: list[dict[str, Any]],
    ) -> list[EvmLog]:
        self._behave.track("get_logs", address, from_block, to_block, abi)
        return await self._behave.execute("get_logs", address, from_block, to_block, abi)
