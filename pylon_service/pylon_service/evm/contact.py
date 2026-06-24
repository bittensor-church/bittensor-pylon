from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol

import structlog
from eth_typing import ABIEvent
from hexbytes import HexBytes
from pylon_commons.models import EvmLog
from pylon_commons.types import evm as evm_types
from web3 import AsyncWeb3
from web3._utils.events import get_event_data
from web3.exceptions import Web3Exception
from web3.providers import AsyncHTTPProvider
from web3.types import LogReceipt
from web3.utils import event_abi_to_log_topic

from pylon_service.evm.exceptions import EvmInvalidAbiError, EvmInvalidAddressError, EvmRpcError
from pylon_service.metrics import Attr, evm_operation_duration, track_operation

logger = structlog.stdlib.get_logger(__name__)

_REQUEST_TIMEOUT_SECONDS = 30


class EvmPort(Protocol):
    async def open(self) -> None: ...
    async def close(self) -> None: ...
    async def get_current_block(self) -> evm_types.BlockNumber: ...
    async def get_logs(
        self,
        address: evm_types.Address,
        from_block: evm_types.BlockNumber,
        to_block: evm_types.BlockNumber,
        abi: list[dict[str, Any]],
    ) -> list[EvmLog]: ...


class AbstractEvmContact(EvmPort, ABC):
    def __init__(self, rpc_url: evm_types.RpcUrl) -> None:
        self.rpc_url = rpc_url

    async def __aenter__(self):
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    @abstractmethod
    async def open(self) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...

    @abstractmethod
    async def get_current_block(self) -> evm_types.BlockNumber: ...

    @abstractmethod
    async def get_logs(
        self,
        address: evm_types.Address,
        from_block: evm_types.BlockNumber,
        to_block: evm_types.BlockNumber,
        abi: list[dict[str, Any]],
    ) -> list[EvmLog]: ...


class EvmContact(AbstractEvmContact):
    def __init__(self, rpc_url: evm_types.RpcUrl) -> None:
        super().__init__(rpc_url)
        self._w3: AsyncWeb3 | None = None

    async def open(self) -> None:
        provider = AsyncHTTPProvider(self.rpc_url, request_kwargs={"timeout": _REQUEST_TIMEOUT_SECONDS})
        self._w3 = AsyncWeb3(provider)

    async def close(self) -> None:
        if self._w3 is not None:
            await self._w3.provider.disconnect()
            self._w3 = None

    @track_operation(evm_operation_duration, labels={"rpc_url": Attr("rpc_url")})
    async def get_current_block(self) -> evm_types.BlockNumber:
        assert self._w3 is not None, "EvmContact is not open"
        return evm_types.BlockNumber(await self._w3.eth.block_number)

    @track_operation(evm_operation_duration, labels={"rpc_url": Attr("rpc_url")})
    async def get_logs(
        self,
        address: evm_types.Address,
        from_block: evm_types.BlockNumber,
        to_block: evm_types.BlockNumber,
        abi: list[dict[str, Any]],
    ) -> list[EvmLog]:
        assert self._w3 is not None, "EvmContact is not open"
        try:
            checksum_address = AsyncWeb3.to_checksum_address(address)
        except ValueError as e:
            raise EvmInvalidAddressError(f"Invalid contract address: {address}") from e
        try:
            event_entries = [ABIEvent(**entry) for entry in abi if entry.get("type") == "event"]
            event_abis: dict[Any, ABIEvent] = {event_abi_to_log_topic(e): e for e in event_entries}
        except Exception as e:
            raise EvmInvalidAbiError(f"Malformed ABI event entry: {e}") from e
        try:
            logs = await self._w3.eth.get_logs(
                {"address": checksum_address, "fromBlock": from_block, "toBlock": to_block}
            )
        except Web3Exception as e:
            raise EvmRpcError(str(e)) from e
        return [decoded for log in logs if (decoded := self._decode_log(self._w3.codec, event_abis, log)) is not None]

    @staticmethod
    def _serialize_arg(value: Any) -> Any:
        if isinstance(value, (bytes, HexBytes)):
            return "0x" + value.hex()
        if isinstance(value, (list, tuple)):
            return [EvmContact._serialize_arg(v) for v in value]
        if isinstance(value, dict):
            return {k: EvmContact._serialize_arg(v) for k, v in value.items()}
        return value

    @staticmethod
    def _decode_log(codec: Any, event_abis: dict[Any, ABIEvent], log: LogReceipt) -> EvmLog | None:
        if not log["topics"]:
            return None
        event_abi = event_abis.get(log["topics"][0])
        if event_abi is None:
            return None
        try:
            decoded = get_event_data(codec, event_abi, log)
        except Exception:
            return None
        return EvmLog(
            event=decoded["event"],
            args={k: EvmContact._serialize_arg(v) for k, v in decoded["args"].items()},
            address=evm_types.Address(decoded["address"]),
            block_number=evm_types.BlockNumber(decoded["blockNumber"]),
            transaction_hash=evm_types.TransactionHash(EvmContact._serialize_arg(decoded["transactionHash"])),
            transaction_index=evm_types.TransactionIndex(decoded["transactionIndex"]),
            log_index=evm_types.LogIndex(decoded["logIndex"]),
        )
