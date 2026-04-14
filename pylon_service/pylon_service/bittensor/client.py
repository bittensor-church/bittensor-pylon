from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, cast

from bittensor_wallet import Wallet
from pylon_commons.constants import LATEST_BLOCK_MARK
from pylon_commons.currency import Currency, Token
from pylon_commons.models import (
    AxonInfo,
    AxonProtocol,
    Block,
    CertificateAlgorithm,
    CommitmentVariant,
    CommitReveal,
    Extrinsic,
    ExtrinsicCall,
    Neuron,
    NeuronCertificate,
    NeuronCertificateKeypair,
    RevealedCommitment,
    Stakes,
    SubnetCommitments,
    SubnetHyperparams,
    SubnetNeurons,
    SubnetRevealedCommitments,
    SubnetState,
    SubnetValidators,
)
from pylon_commons.types import (
    ArchiveBlocksCutoff,
    BittensorNetwork,
    BlockHash,
    BlockNumber,
    Coldkey,
    CommitmentDataBytes,
    Consensus,
    Dividends,
    Emission,
    ExtrinsicHash,
    ExtrinsicIndex,
    ExtrinsicLength,
    Hotkey,
    Incentive,
    NetUid,
    NeuronActive,
    NeuronUid,
    Port,
    PrivateKey,
    PruningScore,
    PublicKey,
    Rank,
    RevealedCommitmentData,
    RevealRound,
    Stake,
    Timestamp,
    Trust,
    ValidatorPermit,
    ValidatorTrust,
    Weight,
)
from turbobt.block import Block as TurboBtBlock
from turbobt.client import Bittensor
from turbobt.neuron import Neuron as TurboBtNeuron
from turbobt.subnet import CertificateAlgorithm as TurboBtCertificateAlgorithm
from turbobt.subnet import Commitment as TurboBtCommitment
from turbobt.subnet import (
    NeuronCertificate as TurboBtNeuronCertificate,
)
from turbobt.subnet import (
    NeuronCertificateKeypair as TurboBtNeuronCertificateKeypair,
)
from turbobt.subnet import (
    SubnetHyperparams as TurboBtSubnetHyperparams,
)
from turbobt.subnet import SubnetState as TurboBtSubnetState
from turbobt.substrate.exceptions import UnknownBlock
from turbobt.substrate.pallets.chain import Extrinsic as TurboBtExtrinsic
from turbobt.substrate.pallets.chain import SignedBlock

from pylon_service.bittensor.exceptions import ArchiveFallbackException
from pylon_service.bittensor.utils import map_to_commitment, map_to_revealed_commitment
from pylon_service.metrics import (
    Attr,
    Param,
    bittensor_fallback_total,
    bittensor_operation_duration,
    track_operation,
)

logger = logging.getLogger(__name__)

unknown_hotkey = Hotkey("N/A")


class AbstractBittensorClient(ABC):
    """
    Interface for Bittensor clients.
    """

    def __init__(self, wallet: Wallet | None, uri: BittensorNetwork):
        self.wallet = wallet
        self.uri = uri
        try:
            self.hotkey = Hotkey(wallet.hotkey.ss58_address) if wallet else unknown_hotkey
        except Exception:
            self.hotkey = unknown_hotkey

    async def __aenter__(self):
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    @abstractmethod
    async def open(self) -> None:
        """
        Opens the client and prepares it for work.
        """

    @abstractmethod
    async def close(self) -> None:
        """
        Closes the client and cleans up resources.
        """

    @abstractmethod
    async def get_block(self, number: BlockNumber) -> Block | None:
        """
        Fetches a block from bittensor.
        """

    @abstractmethod
    async def get_latest_block(self) -> Block:
        """
        Fetches the latest block.
        """

    @abstractmethod
    async def get_block_timestamp(self, block: Block) -> Timestamp:
        """
        Returns the timestamp of a block in seconds.
        """

    @abstractmethod
    async def get_neurons_list(self, netuid: NetUid, block: Block) -> list[Neuron]:
        """
        Fetches all neurons at the given block.
        """

    @abstractmethod
    async def get_hyperparams(self, netuid: NetUid, block: Block) -> SubnetHyperparams | None:
        """
        Fetches subnet's hyperparameters at the given block.
        """

    @abstractmethod
    async def get_certificates(self, netuid: NetUid, block: Block) -> dict[Hotkey, NeuronCertificate]:
        """
        Fetches certificates for all neurons in a subnet.
        """

    @abstractmethod
    async def get_certificate(
        self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None
    ) -> NeuronCertificate | None:
        """
        Fetches certificate for a hotkey in a subnet. If no hotkey is provided, the hotkey of the client's wallet is
        used.
        """

    @abstractmethod
    async def generate_certificate_keypair(
        self, netuid: NetUid, algorithm: CertificateAlgorithm
    ) -> NeuronCertificateKeypair | None:
        """
        Generate a certificate keypair for the app's wallet.
        """

    @abstractmethod
    async def get_subnet_state(self, netuid: NetUid, block: Block) -> SubnetState:
        """
        Fetches subnet's state at the given block.
        """

    @abstractmethod
    async def commit_weights(self, netuid: NetUid, weights: dict[Hotkey, Weight]) -> RevealRound:
        """
        Commits weights. Returns round number when weights have to be revealed.
        """

    @abstractmethod
    async def set_weights(self, netuid: NetUid, weights: dict[Hotkey, Weight]) -> None:
        """
        Sets weights. Used instead of commit_weights for subnets with commit-reveal disabled.
        """

    @abstractmethod
    async def get_neurons(self, netuid: NetUid, block: Block) -> SubnetNeurons:
        """
        Fetches metagraph for a subnet at the given block.
        """

    @abstractmethod
    async def get_commitment(
        self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None
    ) -> CommitmentVariant | None:
        """
        Fetches commitment data for a hotkey in a subnet. If no hotkey is provided, the hotkey of the client's wallet
        is used.
        """

    @abstractmethod
    async def get_revealed_commitments(
        self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None
    ) -> list[RevealedCommitment] | None:
        """
        Fetches revealed commitments for a hotkey in a subnet. If no hotkey is provided, the hotkey of the client's wallet
        is used.
        """

    @abstractmethod
    async def get_commitments(self, netuid: NetUid, block: Block) -> SubnetCommitments:
        """
        Fetches commitments for currently registered hotkeys in a subnet.
        """

    @abstractmethod
    async def get_all_revealed_commitments(self, netuid: NetUid, block: Block) -> SubnetRevealedCommitments:
        """
        Fetches all revealed commitments for a subnet at the given block.
        """

    @abstractmethod
    async def set_commitment(self, netuid: NetUid, data: CommitmentDataBytes) -> None:
        """
        Sets commitment data on chain for the wallet's hotkey.
        """

    @abstractmethod
    async def set_revealed_commitment(
        self, netuid: NetUid, commitment: RevealedCommitmentData, block_to_reveal: int, block_time: int | float
    ) -> int:
        """
        Sets revealed commitment on chain with retry logic.

        Returns:
            Reveal round for revealed commitment created.
        """

    @abstractmethod
    async def get_validators(self, netuid: NetUid, block: Block) -> SubnetValidators:
        """
        Fetches validators (neurons with validator_permit=True) at the given block,
        sorted by total stake in descending order.
        """

    @abstractmethod
    async def get_signed_block(self, block: Block) -> SignedBlock | None:
        """
        Fetches the full signed block data from the chain.

        Args:
            block: The block to fetch.

        Returns:
            The raw signed block data containing header and extrinsics,
            or None if the block could not be fetched.
        """

    @abstractmethod
    async def get_extrinsic(self, block: Block, extrinsic_index: ExtrinsicIndex) -> Extrinsic | None:
        """
        Fetches a decoded extrinsic from a specific block.

        Args:
            block: The block containing the extrinsic.
            extrinsic_index: The index of the extrinsic within the block.

        Returns:
            The decoded extrinsic if found, None if the index is out of bounds.
        """

    @abstractmethod
    async def get_drand_last_stored_round(self, block: Block | None = None) -> int:
        """
        Fetches the last stored drand round from the blockchain.

        Args:
            block: The optional block to query the last stored round at.

        Returns:
            The last stored drand round.
        """


class AbstractTurboBTtransport(ABC):
    @property
    @abstractmethod
    def bittensor(self) -> Bittensor | None:
        """
        Returns the currently opened raw turbobt client instance, if any.
        """

    @abstractmethod
    async def open(self) -> None:
        """
        Opens the transport and prepares it for work.
        """

    @abstractmethod
    async def close(self) -> None:
        """
        Closes the transport and cleans up resources.
        """

    @abstractmethod
    async def get_block(self, number: BlockNumber) -> TurboBtBlock | None:
        """
        Fetches a raw block from turbobt.
        """

    @abstractmethod
    async def get_block_timestamp(self, block_number: BlockNumber) -> datetime:
        """
        Fetches a raw block timestamp from turbobt.
        """

    @abstractmethod
    async def list_neurons(self, netuid: NetUid, block_hash: BlockHash) -> list[TurboBtNeuron]:
        """
        Fetches raw neurons from turbobt.
        """

    @abstractmethod
    async def get_hyperparameters(self, netuid: NetUid, block_hash: BlockHash) -> TurboBtSubnetHyperparams | None:
        """
        Fetches raw subnet hyperparameters from turbobt.
        """

    @abstractmethod
    async def get_certificates(
        self, netuid: NetUid, block_hash: BlockHash
    ) -> dict[str, TurboBtNeuronCertificate] | None:
        """
        Fetches raw certificates from turbobt.
        """

    @abstractmethod
    async def get_certificate(
        self, netuid: NetUid, hotkey: Hotkey, block_hash: BlockHash
    ) -> TurboBtNeuronCertificate | None:
        """
        Fetches a raw certificate from turbobt.
        """

    @abstractmethod
    async def generate_certificate_keypair(
        self, netuid: NetUid, algorithm: TurboBtCertificateAlgorithm
    ) -> TurboBtNeuronCertificateKeypair | None:
        """
        Generates a raw certificate keypair via turbobt.
        """

    @abstractmethod
    async def get_subnet_state(self, netuid: NetUid, block_hash: BlockHash) -> TurboBtSubnetState | None:
        """
        Fetches raw subnet state from turbobt.
        """

    @abstractmethod
    async def commit_weights(self, netuid: NetUid, weights: dict[int, float]) -> int:
        """
        Commits raw uid-indexed weights via turbobt.
        """

    @abstractmethod
    async def set_weights(self, netuid: NetUid, weights: dict[int, float]) -> None:
        """
        Sets raw uid-indexed weights via turbobt.
        """

    @abstractmethod
    async def get_commitment(self, netuid: NetUid, hotkey: Hotkey, block_hash: BlockHash) -> TurboBtCommitment | None:
        """
        Fetches a raw commitment from turbobt.
        """

    @abstractmethod
    async def fetch_commitments(self, netuid: NetUid, block_hash: BlockHash) -> dict[str, TurboBtCommitment]:
        """
        Fetches raw commitments for a subnet from turbobt.
        """

    @abstractmethod
    async def set_commitment(self, netuid: NetUid, data: bytes) -> None:
        """
        Sets raw commitment bytes via turbobt.
        """

    @abstractmethod
    async def get_signed_block(self, block_hash: BlockHash) -> SignedBlock | None:
        """
        Fetches a raw signed block from turbobt.
        """


@dataclass(slots=True)
class _BlockRange[T]:
    start: int
    end: int | None
    value: T

    def contains(self, block_number: int) -> bool:
        if block_number < self.start:
            return False
        return self.end is None or block_number <= self.end


@dataclass(slots=True)
class _MockBlockRecord:
    block: TurboBtBlock


class TurboBTtransport(AbstractTurboBTtransport):
    """
    Raw turbobt transport.
    """

    def __init__(self, wallet: Wallet | None, uri: BittensorNetwork):
        self.wallet = wallet
        self.uri = uri
        self._raw_client: Bittensor | None = None
        self._is_client_ready = asyncio.Event()

    @property
    def bittensor(self) -> Bittensor | None:
        return self._raw_client

    async def _get_bt_client(self) -> Bittensor:
        if self._raw_client is None:
            raise AttributeError(
                "The client is not open, please use the client as a context manager or call the open() method."
            )
        async with asyncio.timeout(5):
            await self._is_client_ready.wait()
        return self._raw_client

    async def open(self) -> None:
        assert self._raw_client is None, "The client is already open."
        logger.info(f"Opening the TurboBTtransport for {self.uri}")
        self._raw_client = Bittensor(wallet=self.wallet, uri=self.uri)
        await asyncio.shield(self._raw_client.__aenter__())
        self._is_client_ready.set()

    async def close(self) -> None:
        logger.info(f"Closing the TurboBTtransport for {self.uri}")
        assert self._raw_client is not None, "The client is already closed."
        async with asyncio.timeout(5):
            await self._is_client_ready.wait()
        bt_client = self._raw_client
        self._raw_client = None
        self._is_client_ready.clear()
        await asyncio.shield(bt_client.__aexit__(None, None, None))

    async def _recreate_bt_client(self) -> None:
        assert self._raw_client is not None, "The client is None so cannot be recreated."
        logger.warning(f"Recreating Bittensor client for {self.uri}")
        if not self._is_client_ready.is_set():
            async with asyncio.timeout(5):
                await self._is_client_ready.wait()
            return
        self._is_client_ready.clear()
        try:
            old_client = self._raw_client
            try:
                await asyncio.shield(old_client.__aexit__(None, None, None))
            except Exception:
                logger.warning("Failed to close old Bittensor client during recreation", exc_info=True)
            self._raw_client = Bittensor(wallet=self.wallet, uri=self.uri)
            await asyncio.shield(self._raw_client.__aenter__())
        finally:
            self._is_client_ready.set()

    async def _protect_turbobt[T](self, coro_factory: Callable[[Bittensor], Awaitable[T]]) -> T:
        bt_client = await self._get_bt_client()
        try:
            return await asyncio.shield(coro_factory(bt_client))
        except RuntimeError:
            logger.exception(f"RuntimeError caught during bittensor operation on {self.uri}, recreating client")
            await asyncio.shield(self._recreate_bt_client())
            bt_client = await self._get_bt_client()
            return await asyncio.shield(coro_factory(bt_client))

    async def get_block(self, number: BlockNumber) -> TurboBtBlock | None:
        return await self._protect_turbobt(lambda c: c.block(number).get())

    async def get_block_timestamp(self, block_number: BlockNumber) -> datetime:
        async def _get_timestamp(bt_client: Bittensor) -> datetime:
            turbobt_block = await bt_client.block(block_number).get()
            return await turbobt_block.get_timestamp()

        return await self._protect_turbobt(_get_timestamp)

    async def list_neurons(self, netuid: NetUid, block_hash: BlockHash) -> list[TurboBtNeuron]:
        return await self._protect_turbobt(lambda c: c.subnet(netuid).list_neurons(block_hash=block_hash))

    async def get_hyperparameters(self, netuid: NetUid, block_hash: BlockHash) -> TurboBtSubnetHyperparams | None:
        return await self._protect_turbobt(lambda c: c.subnet(netuid).get_hyperparameters(block_hash=block_hash))

    async def get_certificates(
        self, netuid: NetUid, block_hash: BlockHash
    ) -> dict[str, TurboBtNeuronCertificate] | None:
        return await self._protect_turbobt(lambda c: c.subnet(netuid).neurons.get_certificates(block_hash=block_hash))

    async def get_certificate(
        self, netuid: NetUid, hotkey: Hotkey, block_hash: BlockHash
    ) -> TurboBtNeuronCertificate | None:
        return await self._protect_turbobt(
            lambda c: c.subnet(netuid).neuron(hotkey=hotkey).get_certificate(block_hash=block_hash)
        )

    async def generate_certificate_keypair(
        self, netuid: NetUid, algorithm: TurboBtCertificateAlgorithm
    ) -> TurboBtNeuronCertificateKeypair | None:
        return await self._protect_turbobt(
            lambda c: c.subnet(netuid).neurons.generate_certificate_keypair(algorithm=algorithm)
        )

    async def get_subnet_state(self, netuid: NetUid, block_hash: BlockHash) -> TurboBtSubnetState | None:
        return await self._protect_turbobt(lambda c: c.subnet(netuid).get_state(block_hash))

    async def commit_weights(self, netuid: NetUid, weights: dict[int, float]) -> int:
        return await self._protect_turbobt(lambda c: c.subnet(netuid).weights.commit(weights))

    async def set_weights(self, netuid: NetUid, weights: dict[int, float]) -> None:
        await self._protect_turbobt(lambda c: c.subnet(netuid).weights.set(weights))

    async def get_commitment(self, netuid: NetUid, hotkey: Hotkey, block_hash: BlockHash) -> TurboBtCommitment | None:
        return await self._protect_turbobt(lambda c: c.subnet(netuid).commitments.get(hotkey, block_hash=block_hash))

    async def fetch_commitments(self, netuid: NetUid, block_hash: BlockHash) -> dict[str, TurboBtCommitment]:
        return await self._protect_turbobt(lambda c: c.subnet(netuid).commitments.fetch(block_hash=block_hash))

    async def set_commitment(self, netuid: NetUid, data: bytes) -> None:
        await self._protect_turbobt(lambda c: c.subnet(netuid).commitments.set(data))

    async def get_signed_block(self, block_hash: BlockHash) -> SignedBlock | None:
        return await self._protect_turbobt(lambda c: c.subtensor.chain.getBlock(block_hash))


class MockTurboBTtransport(AbstractTurboBTtransport):
    """
    Declarative, no-IO transport for tests that exercise the TurboBtClient seam.
    """

    def __init__(self) -> None:
        self._latest_block: TurboBtBlock | None = None
        self._blocks_by_number: dict[int, _MockBlockRecord] = {}
        self._blocks_by_hash: dict[BlockHash, _MockBlockRecord] = {}
        self._neurons: dict[NetUid, list[_BlockRange[list[TurboBtNeuron]]]] = {}
        self._subnet_states: dict[NetUid, list[_BlockRange[TurboBtSubnetState]]] = {}
        self.calls: defaultdict[str, list[tuple[Any, ...]]] = defaultdict(list)

    @property
    def bittensor(self) -> Bittensor | None:
        return None

    def _record_block(self, block: TurboBtBlock) -> None:
        assert block.number is not None, "MockTurboBTtransport requires blocks with a number."
        assert block.hash is not None, "MockTurboBTtransport requires blocks with a hash."
        record = _MockBlockRecord(block=block)
        self._blocks_by_number[int(block.number)] = record
        self._blocks_by_hash[BlockHash(block.hash)] = record

    def _resolve_block_number(self, block_hash: BlockHash) -> int:
        try:
            block_number = self._blocks_by_hash[block_hash].block.number
            assert block_number is not None, "MockTurboBTtransport requires blocks with a number."
            return int(block_number)
        except KeyError as exc:
            raise LookupError(f"No mock block configured for hash {block_hash}") from exc

    @staticmethod
    def _resolve_range[T](ranges: list[_BlockRange[T]], *, block_number: int, what: str) -> T:
        for block_range in reversed(ranges):
            if block_range.contains(block_number):
                return block_range.value
        raise LookupError(f"No mock {what} configured for block {block_number}")

    def set_latest_block(self, block: TurboBtBlock) -> None:
        self._latest_block = block
        self._record_block(block)

    def add_block(self, block: TurboBtBlock) -> None:
        self._record_block(block)

    def add_neurons_range(self, netuid: NetUid, start: int, end: int | None, neurons: list[TurboBtNeuron]) -> None:
        self._neurons.setdefault(netuid, []).append(_BlockRange(start=start, end=end, value=neurons))

    def add_subnet_state_range(self, netuid: NetUid, start: int, end: int | None, state: TurboBtSubnetState) -> None:
        self._subnet_states.setdefault(netuid, []).append(_BlockRange(start=start, end=end, value=state))

    def reset(self) -> None:
        self._latest_block = None
        self._blocks_by_number.clear()
        self._blocks_by_hash.clear()
        self._neurons.clear()
        self._subnet_states.clear()
        self.calls.clear()

    async def open(self) -> None:
        self.calls["open"].append(())

    async def close(self) -> None:
        self.calls["close"].append(())

    async def get_block(self, number: BlockNumber) -> TurboBtBlock | None:
        self.calls["get_block"].append((number,))
        if number == BlockNumber(LATEST_BLOCK_MARK):
            return self._latest_block
        record = self._blocks_by_number.get(int(number))
        return record and record.block

    async def get_block_timestamp(self, block_number: BlockNumber) -> datetime:
        self.calls["get_block_timestamp"].append((block_number,))
        raise NotImplementedError("MockTurboBTtransport does not implement get_block_timestamp in this change")

    async def list_neurons(self, netuid: NetUid, block_hash: BlockHash) -> list[TurboBtNeuron]:
        self.calls["list_neurons"].append((netuid, block_hash))
        try:
            ranges = self._neurons[netuid]
        except KeyError as exc:
            raise LookupError(f"No mock neurons configured for subnet {netuid}") from exc
        block_number = self._resolve_block_number(block_hash)
        return self._resolve_range(ranges, block_number=block_number, what=f"neurons for subnet {netuid}")

    async def get_hyperparameters(self, netuid: NetUid, block_hash: BlockHash) -> TurboBtSubnetHyperparams | None:
        self.calls["get_hyperparameters"].append((netuid, block_hash))
        raise NotImplementedError("MockTurboBTtransport does not implement get_hyperparameters in this change")

    async def get_certificates(
        self, netuid: NetUid, block_hash: BlockHash
    ) -> dict[str, TurboBtNeuronCertificate] | None:
        self.calls["get_certificates"].append((netuid, block_hash))
        raise NotImplementedError("MockTurboBTtransport does not implement get_certificates in this change")

    async def get_certificate(
        self, netuid: NetUid, hotkey: Hotkey, block_hash: BlockHash
    ) -> TurboBtNeuronCertificate | None:
        self.calls["get_certificate"].append((netuid, hotkey, block_hash))
        raise NotImplementedError("MockTurboBTtransport does not implement get_certificate in this change")

    async def generate_certificate_keypair(
        self, netuid: NetUid, algorithm: TurboBtCertificateAlgorithm
    ) -> TurboBtNeuronCertificateKeypair | None:
        self.calls["generate_certificate_keypair"].append((netuid, algorithm))
        raise NotImplementedError("MockTurboBTtransport does not implement generate_certificate_keypair in this change")

    async def get_subnet_state(self, netuid: NetUid, block_hash: BlockHash) -> TurboBtSubnetState:
        self.calls["get_subnet_state"].append((netuid, block_hash))
        try:
            ranges = self._subnet_states[netuid]
        except KeyError as exc:
            raise LookupError(f"No mock subnet state configured for subnet {netuid}") from exc
        block_number = self._resolve_block_number(block_hash)
        return self._resolve_range(ranges, block_number=block_number, what=f"subnet state for subnet {netuid}")

    async def commit_weights(self, netuid: NetUid, weights: dict[int, float]) -> int:
        self.calls["commit_weights"].append((netuid, weights))
        raise NotImplementedError("MockTurboBTtransport does not implement commit_weights in this change")

    async def set_weights(self, netuid: NetUid, weights: dict[int, float]) -> None:
        self.calls["set_weights"].append((netuid, weights))
        raise NotImplementedError("MockTurboBTtransport does not implement set_weights in this change")

    async def get_commitment(self, netuid: NetUid, hotkey: Hotkey, block_hash: BlockHash) -> TurboBtCommitment | None:
        self.calls["get_commitment"].append((netuid, hotkey, block_hash))
        raise NotImplementedError("MockTurboBTtransport does not implement get_commitment in this change")

    async def fetch_commitments(self, netuid: NetUid, block_hash: BlockHash) -> dict[str, TurboBtCommitment]:
        self.calls["fetch_commitments"].append((netuid, block_hash))
        raise NotImplementedError("MockTurboBTtransport does not implement fetch_commitments in this change")

    async def set_commitment(self, netuid: NetUid, data: bytes) -> None:
        self.calls["set_commitment"].append((netuid, data))
        raise NotImplementedError("MockTurboBTtransport does not implement set_commitment in this change")

    async def get_signed_block(self, block_hash: BlockHash) -> SignedBlock | None:
        self.calls["get_signed_block"].append((block_hash,))
        raise NotImplementedError("MockTurboBTtransport does not implement get_signed_block in this change")


def get_turbobt_transport(wallet: Wallet | None, uri: BittensorNetwork) -> AbstractTurboBTtransport:
    return TurboBTtransport(wallet=wallet, uri=uri)


class TurboBtClient(AbstractBittensorClient):
    """
    Adapter for turbobt client.
    """

    def __init__(
        self,
        wallet: Wallet | None,
        uri: BittensorNetwork,
        transport: AbstractTurboBTtransport | None = None,
    ):
        super().__init__(wallet, uri)
        self._transport = transport or get_turbobt_transport(wallet=wallet, uri=uri)

    @property
    def bittensor(self) -> Bittensor | None:
        return self._transport.bittensor

    @property
    def _raw_client(self) -> Bittensor | None:
        return self.bittensor

    @property
    def _is_client_ready(self) -> asyncio.Event:
        if isinstance(self._transport, TurboBTtransport):
            return self._transport._is_client_ready
        raise AttributeError("Transport does not expose readiness event.")

    def _require_concrete_transport(self) -> TurboBTtransport:
        if isinstance(self._transport, TurboBTtransport):
            return self._transport
        raise AttributeError("Transport does not expose concrete turbobt internals.")

    async def _get_bt_client(self) -> Bittensor:
        return await self._require_concrete_transport()._get_bt_client()

    async def open(self) -> None:
        await self._transport.open()

    async def close(self) -> None:
        await self._transport.close()

    async def _recreate_bt_client(self) -> None:
        await self._require_concrete_transport()._recreate_bt_client()

    def _resolve_hotkey(self, hotkey: Hotkey | None) -> Hotkey:
        if hotkey:
            return hotkey
        if self.wallet is None:
            raise ValueError("No hotkey provided while the client has no wallet.")
        return Hotkey(self.wallet.hotkey.ss58_address)

    @track_operation(
        bittensor_operation_duration,
        labels={
            "uri": Attr("uri"),
            "hotkey": Attr("hotkey"),
        },
    )
    async def get_block(self, number: BlockNumber) -> Block | None:
        logger.debug(f"Fetching the block with number {number} from {self.uri}")
        block_obj = await self._transport.get_block(number)
        if block_obj is None or block_obj.number is None or block_obj.hash is None:
            return None
        return Block(
            number=BlockNumber(block_obj.number),
            hash=BlockHash(block_obj.hash),
        )

    @track_operation(
        bittensor_operation_duration,
        labels={
            "uri": Attr("uri"),
            "hotkey": Attr("hotkey"),
        },
    )
    async def get_latest_block(self) -> Block:
        logger.debug(f"Fetching the latest block from {self.uri}")
        block = await self.get_block(BlockNumber(LATEST_BLOCK_MARK))
        assert block is not None, "Latest block should always exist"
        return block

    async def get_block_timestamp(self, block: Block) -> Timestamp:
        timestamp = await self._transport.get_block_timestamp(block.number)
        return Timestamp(int(timestamp.timestamp()))

    @staticmethod
    async def _translate_neuron(neuron: TurboBtNeuron, stakes: Stakes) -> Neuron:
        return Neuron(
            uid=NeuronUid(neuron.uid),
            coldkey=Coldkey(neuron.coldkey),
            hotkey=Hotkey(neuron.hotkey),
            active=NeuronActive(neuron.active),
            axon_info=AxonInfo(
                ip=neuron.axon_info.ip,
                port=Port(neuron.axon_info.port),
                protocol=AxonProtocol(neuron.axon_info.protocol),
            ),
            stake=Stake(neuron.stake),
            rank=Rank(neuron.rank),
            emission=Emission(Currency[Token.ALPHA](neuron.emission)),
            incentive=Incentive(neuron.incentive),
            consensus=Consensus(neuron.consensus),
            trust=Trust(neuron.trust),
            validator_trust=ValidatorTrust(neuron.validator_trust),
            dividends=Dividends(neuron.dividends),
            last_update=Timestamp(neuron.last_update),
            validator_permit=ValidatorPermit(neuron.validator_permit),
            pruning_score=PruningScore(neuron.pruning_score),
            stakes=stakes,
        )

    @track_operation(
        bittensor_operation_duration,
        labels={
            "uri": Attr("uri"),
            "netuid": Param("netuid"),
            "hotkey": Attr("hotkey"),
        },
    )
    async def get_neurons_list(self, netuid: NetUid, block: Block) -> list[Neuron]:
        logger.debug(f"Fetching neurons from subnet {netuid} at block {block.number}, {self.uri}")
        neurons = await self._transport.list_neurons(netuid, block.hash)
        # We need stakes fetched from subnet's state.
        state = await self.get_subnet_state(netuid, block)
        stakes = state.hotkeys_stakes
        return [await self._translate_neuron(neuron, stakes[Hotkey(neuron.hotkey)]) for neuron in neurons]

    @track_operation(
        bittensor_operation_duration,
        labels={
            "uri": Attr("uri"),
            "netuid": Param("netuid"),
            "hotkey": Attr("hotkey"),
        },
    )
    async def get_neurons(self, netuid: NetUid, block: Block) -> SubnetNeurons:
        neurons = await self.get_neurons_list(netuid, block)
        return SubnetNeurons(block=block, neurons={neuron.hotkey: neuron for neuron in neurons})

    @staticmethod
    async def _translate_hyperparams(params: TurboBtSubnetHyperparams) -> SubnetHyperparams:
        translated_params: dict[str, Any] = dict(params)
        if (commit_reveal := translated_params.get("commit_reveal_weights_enabled")) is not None:
            translated_params["commit_reveal_weights_enabled"] = (
                CommitReveal.V4 if commit_reveal else CommitReveal.DISABLED
            )
        return SubnetHyperparams(**translated_params)

    @track_operation(
        bittensor_operation_duration,
        labels={
            "uri": Attr("uri"),
            "netuid": Param("netuid"),
            "hotkey": Attr("hotkey"),
        },
    )
    async def get_hyperparams(self, netuid: NetUid, block: Block) -> SubnetHyperparams | None:
        logger.debug(f"Fetching hyperparams from subnet {netuid} at block {block.number}, {self.uri}")
        params = await self._transport.get_hyperparameters(netuid, block.hash)
        if not params:
            return None
        return await self._translate_hyperparams(params)

    @staticmethod
    async def _translate_certificate(certificate: TurboBtNeuronCertificate) -> NeuronCertificate:
        return NeuronCertificate(
            algorithm=CertificateAlgorithm(certificate["algorithm"]),
            public_key=PublicKey(certificate["public_key"]),
        )

    @track_operation(
        bittensor_operation_duration,
        labels={
            "uri": Attr("uri"),
            "netuid": Param("netuid"),
            "hotkey": Attr("hotkey"),
        },
    )
    async def get_certificates(self, netuid: NetUid, block: Block) -> dict[Hotkey, NeuronCertificate]:
        logger.debug(f"Fetching certificates from subnet {netuid} at block {block.number}, {self.uri}")
        certificates = await self._transport.get_certificates(netuid, block.hash)
        if not certificates:
            return {}
        return {
            Hotkey(hotkey): await self._translate_certificate(certificate)
            for hotkey, certificate in certificates.items()
        }

    @track_operation(
        bittensor_operation_duration,
        labels={
            "uri": Attr("uri"),
            "netuid": Param("netuid"),
            "hotkey": Attr("hotkey"),
        },
    )
    async def get_certificate(
        self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None
    ) -> NeuronCertificate | None:
        hotkey = self._resolve_hotkey(hotkey)
        logger.debug(
            f"Fetching certificate of {hotkey} hotkey from subnet {netuid} at block {block.number}, {self.uri}"
        )
        certificate = await self._transport.get_certificate(netuid, hotkey, block.hash)
        if certificate:
            certificate = await self._translate_certificate(certificate)
        return certificate

    @staticmethod
    async def _translate_certificate_keypair(keypair: TurboBtNeuronCertificateKeypair) -> NeuronCertificateKeypair:
        return NeuronCertificateKeypair(
            algorithm=CertificateAlgorithm(keypair["algorithm"]),
            public_key=PublicKey(keypair["public_key"]),
            private_key=PrivateKey(keypair["private_key"]),
        )

    @track_operation(
        bittensor_operation_duration,
        labels={
            "uri": Attr("uri"),
            "netuid": Param("netuid"),
            "hotkey": Attr("hotkey"),
        },
    )
    async def generate_certificate_keypair(
        self, netuid: NetUid, algorithm: CertificateAlgorithm
    ) -> NeuronCertificateKeypair | None:
        logger.debug(f"Generating certificate on subnet {netuid} at {self.uri}")
        keypair = await self._transport.generate_certificate_keypair(
            netuid,
            TurboBtCertificateAlgorithm(algorithm),
        )
        if keypair:
            keypair = await self._translate_certificate_keypair(keypair)
        return keypair

    @track_operation(
        bittensor_operation_duration,
        labels={
            "uri": Attr("uri"),
            "netuid": Param("netuid"),
            "hotkey": Attr("hotkey"),
        },
    )
    async def get_subnet_state(self, netuid: NetUid, block: Block) -> SubnetState:
        logger.debug(f"Fetching subnet {netuid} state at block {block.number}, {self.uri}")
        state = await self._transport.get_subnet_state(netuid, block.hash)
        if state is None:
            raise LookupError(f"Subnet {netuid} state not found at block {block.number}.")
        return SubnetState(**cast(dict[str, Any], state))

    async def _translate_weights(self, netuid: NetUid, weights: dict[Hotkey, Weight]) -> dict[int, float]:
        translated_weights = {}
        missing = []
        latest_block = await self.get_latest_block()
        neurons = await self._transport.list_neurons(netuid, latest_block.hash)
        hotkey_to_uid = {n.hotkey: n.uid for n in neurons}
        for hotkey, weight in weights.items():
            if hotkey in hotkey_to_uid:
                translated_weights[hotkey_to_uid[hotkey]] = weight
            else:
                missing.append(hotkey)
        if missing:
            logger.warning(
                "Some of the hotkeys passed for weight commitment are missing. "
                f"Weights will not be commited for the following hotkeys: {missing}."
            )
        return translated_weights

    @track_operation(
        bittensor_operation_duration,
        labels={
            "uri": Attr("uri"),
            "netuid": Param("netuid"),
            "hotkey": Attr("hotkey"),
        },
    )
    async def commit_weights(self, netuid: NetUid, weights: dict[Hotkey, Weight]) -> RevealRound:
        logger.debug(f"Commiting weights on subnet {netuid} at {self.uri}")
        translated_weights = await self._translate_weights(netuid, weights)
        reveal_round = await self._transport.commit_weights(netuid, translated_weights)
        return RevealRound(reveal_round)

    @track_operation(
        bittensor_operation_duration,
        labels={
            "uri": Attr("uri"),
            "netuid": Param("netuid"),
            "hotkey": Attr("hotkey"),
        },
    )
    async def set_weights(self, netuid: NetUid, weights: dict[Hotkey, Weight]) -> None:
        logger.debug(f"Setting weights on subnet {netuid} at {self.uri}")
        translated_weights = await self._translate_weights(netuid, weights)
        await self._transport.set_weights(netuid, translated_weights)

    @track_operation(
        bittensor_operation_duration,
        labels={
            "uri": Attr("uri"),
            "netuid": Param("netuid"),
            "hotkey": Attr("hotkey"),
        },
    )
    async def get_commitment(
        self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None
    ) -> CommitmentVariant | None:
        hotkey = self._resolve_hotkey(hotkey)
        logger.debug(f"Fetching commitment for {hotkey} from subnet {netuid} at block {block.number}, {self.uri}")
        result = await self._transport.get_commitment(netuid, hotkey, block.hash)
        if result is None:
            return None
        return map_to_commitment(result, hotkey)

    @track_operation(
        bittensor_operation_duration,
        labels={
            "uri": Attr("uri"),
            "netuid": Param("netuid"),
            "hotkey": Attr("hotkey"),
        },
    )
    async def get_revealed_commitments(
        self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None
    ) -> list[RevealedCommitment] | None:
        hotkey = self._resolve_hotkey(hotkey)
        logger.debug(
            f"Fetching revealed commitments for {hotkey} from subnet {netuid} at block {block.number}, {self.uri}"
        )
        results = await self._protect_turbobt(
            lambda c: c.subnet(netuid).commitments.get_revealed(hotkey, block_hash=block.hash)
        )
        if results is None:
            return None
        return [map_to_revealed_commitment(result, hotkey) for result in results]

    @track_operation(
        bittensor_operation_duration,
        labels={
            "uri": Attr("uri"),
            "netuid": Param("netuid"),
            "hotkey": Attr("hotkey"),
        },
    )
    async def get_commitments(self, netuid: NetUid, block: Block) -> SubnetCommitments:
        logger.debug(f"Fetching all commitments from subnet {netuid} at block {block.number}, {self.uri}")
        raw_commitments, state = await asyncio.gather(
            self._transport.fetch_commitments(netuid, block.hash),
            self.get_subnet_state(netuid, block),
        )
        registered_hotkeys = set(state.hotkeys)
        commitments = {
            hotkey: map_to_commitment(result, hotkey)
            for hotkey_str, result in raw_commitments.items()
            if (hotkey := Hotkey(hotkey_str)) in registered_hotkeys
        }
        return SubnetCommitments(block=block, commitments=commitments)

    @track_operation(
        bittensor_operation_duration,
        labels={
            "uri": Attr("uri"),
            "netuid": Param("netuid"),
            "hotkey": Attr("hotkey"),
        },
    )
    async def get_all_revealed_commitments(self, netuid: NetUid, block: Block) -> SubnetRevealedCommitments:
        logger.debug(f"Fetching all revealed commitments from subnet {netuid} at block {block.number}, {self.uri}")
        raw_commitments, state = await asyncio.gather(
            self._protect_turbobt(lambda c: c.subnet(netuid).commitments.fetch_revealed(block_hash=block.hash)),
            self.get_subnet_state(netuid, block),
        )
        registered_hotkeys = set(state.hotkeys)
        commitments: dict[Hotkey, list[RevealedCommitment]] = {}
        for hotkey_str, results in raw_commitments.items():
            hotkey = Hotkey(hotkey_str)
            if hotkey not in registered_hotkeys:
                continue
            commitments[hotkey] = [map_to_revealed_commitment(result, hotkey) for result in results]
        return SubnetRevealedCommitments(block=block, commitments=commitments)

    @track_operation(
        bittensor_operation_duration,
        labels={
            "uri": Attr("uri"),
            "netuid": Param("netuid"),
            "hotkey": Attr("hotkey"),
        },
    )
    async def set_commitment(self, netuid: NetUid, data: CommitmentDataBytes) -> None:
        logger.debug(f"Setting commitment on subnet {netuid} at {self.uri}")
        # Convert to plain bytes because scalecodec uses `type(value) is bytes` check
        # which fails for bytes subclasses like CommitmentDataBytes
        await self._transport.set_commitment(netuid, bytes(data))

    @track_operation(
        bittensor_operation_duration,
        labels={
            "uri": Attr("uri"),
            "netuid": Param("netuid"),
            "hotkey": Attr("hotkey"),
        },
    )
    async def set_revealed_commitment(
        self, netuid: NetUid, commitment: RevealedCommitmentData, block_to_reveal: int, block_time: int | float
    ) -> int:
        logger.debug(f"Setting revealed commitment on subnet {netuid} at {self.uri}")
        return await self._protect_turbobt(
            lambda c: c.subnet(netuid).commitments.set_revealed(commitment, block_to_reveal, block_time)
        )

    @track_operation(
        bittensor_operation_duration,
        labels={
            "uri": Attr("uri"),
            "netuid": Param("netuid"),
            "hotkey": Attr("hotkey"),
        },
    )
    async def get_validators(self, netuid: NetUid, block: Block) -> SubnetValidators:
        logger.debug(f"Fetching validators from subnet {netuid} at block {block.number}, {self.uri}")
        subnet_neurons = await self.get_neurons(netuid, block=block)
        validators = [n for n in subnet_neurons.neurons.values() if n.validator_permit]
        validators.sort(key=lambda n: n.stakes.total, reverse=True)
        return SubnetValidators(block=block, validators=validators)

    async def get_signed_block(self, block: Block) -> SignedBlock | None:
        logger.debug(f"Fetching signed block {block.number} at {self.uri}")
        return await self._transport.get_signed_block(block.hash)

    async def get_extrinsic(self, block: Block, extrinsic_index: ExtrinsicIndex) -> Extrinsic | None:
        logger.debug(f"Fetching extrinsic {extrinsic_index} from block {block.number} at {self.uri}")

        signed_block = await self.get_signed_block(block)
        if signed_block is None:
            return None

        extrinsics: list[TurboBtExtrinsic] = signed_block["block"]["extrinsics"]  # type: ignore[assignment]
        if extrinsic_index >= len(extrinsics):
            return None

        raw_extrinsic = extrinsics[extrinsic_index]
        return self._translate_extrinsic(raw_extrinsic, block.number, extrinsic_index)

    async def get_drand_last_stored_round(self, block: Block | None = None) -> int:
        logger.debug(f"Fetching last stored drand round at {self.uri}")
        return await self._protect_turbobt(lambda c: c.drand.get_last_stored_round(block.hash if block else None))

    @staticmethod
    def _translate_extrinsic(
        raw_extrinsic: TurboBtExtrinsic, block_number: BlockNumber, extrinsic_index: ExtrinsicIndex
    ) -> Extrinsic:
        """
        Translates a raw decoded extrinsic dict to an Extrinsic model.
        """
        call_data = raw_extrinsic.get("call", {})
        call = ExtrinsicCall(
            call_module=call_data.get("call_module", ""),
            call_function=call_data.get("call_function", ""),
            call_args=call_data.get("call_args", []),
            **{k: v for k, v in call_data.items() if k not in ("call_module", "call_function", "call_args")},
        )

        return Extrinsic(
            block_number=block_number,
            extrinsic_index=extrinsic_index,
            extrinsic_hash=ExtrinsicHash(raw_extrinsic.get("extrinsic_hash", "")),
            extrinsic_length=ExtrinsicLength(raw_extrinsic.get("extrinsic_length", 0)),
            address=raw_extrinsic.get("address"),
            call=call,
            **{
                k: v
                for k, v in raw_extrinsic.items()
                if k not in ("extrinsic_hash", "extrinsic_length", "address", "call")
            },
        )


class FallbackReason(StrEnum):
    STALE_BLOCK = "stale_block"
    UNKNOWN_BLOCK = "unknown_block"


class BittensorClient[SubClient: AbstractBittensorClient](AbstractBittensorClient):
    """
    Bittensor client with archive node fallback support.

    This is a wrapper that delegates to two underlying
    client instances (main and archive) and handles fallback logic.
    """

    def __init__(
        self,
        wallet: Wallet | None,
        uri: BittensorNetwork,
        archive_uri: BittensorNetwork,
        archive_blocks_cutoff: ArchiveBlocksCutoff = ArchiveBlocksCutoff(300),
        subclient_cls: type[SubClient] = TurboBtClient,
    ):
        super().__init__(wallet, uri)
        self.archive_uri = archive_uri
        self._archive_blocks_cutoff = archive_blocks_cutoff
        self.subclient_cls = subclient_cls
        self._main_client: SubClient = self.subclient_cls(wallet, uri)
        self._archive_client: SubClient = self.subclient_cls(wallet, archive_uri)

    async def open(self) -> None:
        await self._main_client.open()
        await self._archive_client.open()

    async def close(self) -> None:
        await self._main_client.close()
        await self._archive_client.close()

    async def get_block(self, number: BlockNumber) -> Block | None:
        return await self._delegate(self.subclient_cls.get_block, number=number)

    async def get_latest_block(self) -> Block:
        return await self._delegate(self.subclient_cls.get_latest_block)

    async def get_neurons_list(self, netuid: NetUid, block: Block) -> list[Neuron]:
        return await self._delegate(self.subclient_cls.get_neurons_list, netuid=netuid, block=block)

    async def get_hyperparams(self, netuid: NetUid, block: Block) -> SubnetHyperparams | None:
        return await self._delegate(self.subclient_cls.get_hyperparams, netuid=netuid, block=block)

    async def get_certificates(self, netuid: NetUid, block: Block) -> dict[Hotkey, NeuronCertificate]:
        return await self._delegate(self.subclient_cls.get_certificates, netuid=netuid, block=block)

    async def get_certificate(
        self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None
    ) -> NeuronCertificate | None:
        return await self._delegate(self.subclient_cls.get_certificate, netuid=netuid, block=block, hotkey=hotkey)

    async def generate_certificate_keypair(
        self, netuid: NetUid, algorithm: CertificateAlgorithm
    ) -> NeuronCertificateKeypair | None:
        return await self._delegate(self.subclient_cls.generate_certificate_keypair, netuid=netuid, algorithm=algorithm)

    async def commit_weights(self, netuid: NetUid, weights: dict[Hotkey, Weight]) -> RevealRound:
        return await self._delegate(self.subclient_cls.commit_weights, netuid=netuid, weights=weights)

    async def set_weights(self, netuid: NetUid, weights: dict[Hotkey, Weight]) -> None:
        return await self._delegate(self.subclient_cls.set_weights, netuid=netuid, weights=weights)

    async def get_neurons(self, netuid: NetUid, block: Block) -> SubnetNeurons:
        return await self._delegate(self.subclient_cls.get_neurons, netuid=netuid, block=block)

    async def get_subnet_state(self, netuid: NetUid, block: Block) -> SubnetState:
        return await self._delegate(self.subclient_cls.get_subnet_state, netuid=netuid, block=block)

    async def get_block_timestamp(self, block: Block) -> Timestamp:
        return await self._delegate(self.subclient_cls.get_block_timestamp, block=block)

    async def get_commitment(
        self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None
    ) -> CommitmentVariant | None:
        return await self._delegate(self.subclient_cls.get_commitment, netuid=netuid, block=block, hotkey=hotkey)

    async def get_revealed_commitments(
        self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None
    ) -> list[RevealedCommitment] | None:
        return await self._delegate(
            self.subclient_cls.get_revealed_commitments, netuid=netuid, block=block, hotkey=hotkey
        )

    async def get_commitments(self, netuid: NetUid, block: Block) -> SubnetCommitments:
        return await self._delegate(self.subclient_cls.get_commitments, netuid=netuid, block=block)

    async def get_all_revealed_commitments(self, netuid: NetUid, block: Block) -> SubnetRevealedCommitments:
        return await self._delegate(self.subclient_cls.get_all_revealed_commitments, netuid=netuid, block=block)

    async def set_commitment(self, netuid: NetUid, data: CommitmentDataBytes) -> None:
        return await self._delegate(self.subclient_cls.set_commitment, netuid=netuid, data=data)

    async def set_revealed_commitment(
        self, netuid: NetUid, commitment: RevealedCommitmentData, block_to_reveal: int, block_time: int | float
    ) -> int:
        return await self._delegate(
            self.subclient_cls.set_revealed_commitment,
            netuid=netuid,
            commitment=commitment,
            block_to_reveal=block_to_reveal,
            block_time=block_time,
        )

    async def get_validators(self, netuid: NetUid, block: Block) -> SubnetValidators:
        return await self._delegate(self.subclient_cls.get_validators, netuid=netuid, block=block)

    async def get_signed_block(self, block: Block) -> SignedBlock | None:
        return await self._delegate(self.subclient_cls.get_signed_block, block=block)

    async def get_extrinsic(self, block: Block, extrinsic_index: ExtrinsicIndex) -> Extrinsic | None:
        return await self._delegate(self.subclient_cls.get_extrinsic, block=block, extrinsic_index=extrinsic_index)

    async def get_drand_last_stored_round(self, block: Block | None = None) -> int:
        return await self._delegate(self.subclient_cls.get_drand_last_stored_round, block=block)

    async def _delegate[DelegateReturn](
        self, operation: Callable[..., Awaitable[DelegateReturn]], *args, block: Block | None = None, **kwargs
    ) -> DelegateReturn:
        """
        Execute operation with a proper client.

        Operations that does not need a block are executed by the main client.
        Archive client is used when the block is stale (older than archive_blocks_cutoff blocks).
        Operations on the main client are retried if UnknownBlock exception is raised.

        Raises:
            ArchiveFallbackException: When block data is unavailable on both main and archive nodes.
        """
        operation_name = operation.__name__

        if block:
            kwargs["block"] = block
            latest_block = await self._main_client.get_latest_block()
            if latest_block.number - block.number > self._archive_blocks_cutoff:
                logger.debug(
                    f"Block {block.number} is stale, falling back to the archive client: {self._archive_client.uri}"
                )
                bittensor_fallback_total.labels(
                    reason=FallbackReason.STALE_BLOCK,
                    operation=operation_name,
                    hotkey=self.hotkey,
                ).inc()
                try:
                    return await operation(self._archive_client, *args, **kwargs)
                except UnknownBlock as e:
                    raise ArchiveFallbackException(
                        detail=(
                            f"Block {block.number} data is unavailable on the archive node. "
                            "Archive was used because the block exceeded archive block cutoff "
                            f"({self._archive_blocks_cutoff} blocks)."
                        )
                    ) from e

        try:
            return await operation(self._main_client, *args, **kwargs)
        except UnknownBlock:
            assert block, "UnknownBlock exception raised by operation that does not use a block!"
            logger.warning(
                f"Block {block.number} unknown for the main client, "
                f"falling back to the archive client: {self._archive_client.uri}"
            )
            bittensor_fallback_total.labels(
                reason=FallbackReason.UNKNOWN_BLOCK,
                operation=operation_name,
                hotkey=self.hotkey,
            ).inc()
            try:
                return await operation(self._archive_client, *args, **kwargs)
            except UnknownBlock as e:
                raise ArchiveFallbackException(
                    detail=f"Block {block.number} data is unavailable on both main and archive nodes."
                ) from e
