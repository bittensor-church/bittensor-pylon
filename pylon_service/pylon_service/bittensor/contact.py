from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol

from bittensor_wallet import Wallet
from pylon_commons.constants import LATEST_BLOCK_MARK
from pylon_commons.currency import Currency, Token
from pylon_commons.models import CommitmentVariant, RevealedCommitment, SubnetRevealedCommitments
from pylon_commons.types import (
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
from turbobt.subnet import NeuronCertificate as TurboBtNeuronCertificate
from turbobt.subnet import NeuronCertificateKeypair as TurboBtNeuronCertificateKeypair
from turbobt.subnet import SubnetHyperparams as TurboBtSubnetHyperparams
from turbobt.substrate.pallets.chain import Extrinsic as TurboBtExtrinsic
from turbobt.substrate.pallets.chain import SignedBlock
from websockets.exceptions import ConnectionClosed

from pylon_service.bittensor.exceptions import BittensorTransportError
from pylon_service.bittensor.models import (
    AxonInfo,
    AxonProtocol,
    Block,
    CertificateAlgorithm,
    CommitReveal,
    Extrinsic,
    ExtrinsicCall,
    Neuron,
    NeuronCertificate,
    NeuronCertificateKeypair,
    Stakes,
    SubnetCommitments,
    SubnetHyperparams,
    SubnetNeurons,
    SubnetState,
)
from pylon_service.bittensor.utils import map_to_commitment, map_to_revealed_commitment
from pylon_service.metrics import Attr, Param, bittensor_operation_duration, track_operation

logger = logging.getLogger(__name__)

unknown_hotkey = Hotkey("N/A")
RECONNECT_EXCEPTIONS = (AttributeError, ConnectionClosed, OSError, RuntimeError)


class AbstractBittensorContact(ABC):
    """
    Thin external-service boundary for Bittensor/Subtensor transport.
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
    async def open(self) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...

    @abstractmethod
    async def get_block(self, number: BlockNumber) -> Block | None: ...

    @abstractmethod
    async def get_latest_block(self) -> Block: ...

    @abstractmethod
    async def get_block_timestamp(self, block: Block) -> Timestamp: ...

    @abstractmethod
    async def get_neurons_list(self, netuid: NetUid, block: Block) -> list[Neuron]: ...

    @abstractmethod
    async def get_hyperparams(self, netuid: NetUid, block: Block) -> SubnetHyperparams | None: ...

    @abstractmethod
    async def get_certificates(self, netuid: NetUid, block: Block) -> dict[Hotkey, NeuronCertificate]: ...

    @abstractmethod
    async def get_certificate(
        self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None
    ) -> NeuronCertificate | None: ...

    @abstractmethod
    async def generate_certificate_keypair(
        self, netuid: NetUid, algorithm: CertificateAlgorithm
    ) -> NeuronCertificateKeypair | None: ...

    @abstractmethod
    async def get_subnet_state(self, netuid: NetUid, block: Block) -> SubnetState: ...

    @abstractmethod
    async def commit_weights(self, netuid: NetUid, weights: dict[NeuronUid, Weight]) -> RevealRound: ...

    @abstractmethod
    async def set_weights(self, netuid: NetUid, weights: dict[NeuronUid, Weight]) -> None: ...

    @abstractmethod
    async def get_neurons(self, netuid: NetUid, block: Block) -> SubnetNeurons: ...

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
    async def get_all_revealed_commitments(self, netuid: NetUid, block: Block) -> SubnetRevealedCommitments:
        """
        Fetches all revealed commitments for a subnet at the given block.
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
    async def get_drand_last_stored_round(self, block: Block | None = None) -> int:
        """
        Fetches the last stored drand round from the blockchain.

        Args:
            block: The optional block to query the last stored round at.

        Returns:
            The last stored drand round.
        """

    @abstractmethod
    async def get_commitments(self, netuid: NetUid, block: Block) -> SubnetCommitments: ...

    @abstractmethod
    async def set_commitment(self, netuid: NetUid, data: CommitmentDataBytes) -> None: ...

    @abstractmethod
    async def get_signed_block(self, block: Block) -> SignedBlock | None: ...

    @abstractmethod
    async def get_extrinsic(self, block: Block, extrinsic_index: ExtrinsicIndex) -> Extrinsic | None: ...


class BittensorPort(Protocol):
    wallet: Wallet | None
    hotkey: Hotkey

    async def get_block(self, number: BlockNumber) -> Block | None: ...
    async def get_latest_block(self) -> Block: ...
    async def get_block_timestamp(self, block: Block) -> Timestamp: ...
    async def get_neurons_list(self, netuid: NetUid, block: Block) -> list[Neuron]: ...
    async def get_hyperparams(self, netuid: NetUid, block: Block) -> SubnetHyperparams | None: ...
    async def get_certificates(self, netuid: NetUid, block: Block) -> dict[Hotkey, NeuronCertificate]: ...
    async def get_certificate(
        self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None
    ) -> NeuronCertificate | None: ...
    async def generate_certificate_keypair(
        self, netuid: NetUid, algorithm: CertificateAlgorithm
    ) -> NeuronCertificateKeypair | None: ...
    async def get_subnet_state(self, netuid: NetUid, block: Block) -> SubnetState: ...
    async def commit_weights(self, netuid: NetUid, weights: dict[NeuronUid, Weight]) -> RevealRound: ...
    async def set_weights(self, netuid: NetUid, weights: dict[NeuronUid, Weight]) -> None: ...
    async def get_neurons(self, netuid: NetUid, block: Block) -> SubnetNeurons: ...
    async def get_commitment(
        self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None
    ) -> CommitmentVariant | None: ...
    async def get_commitments(self, netuid: NetUid, block: Block) -> SubnetCommitments: ...
    async def set_commitment(self, netuid: NetUid, data: CommitmentDataBytes) -> None: ...
    async def get_signed_block(self, block: Block) -> SignedBlock | None: ...
    async def get_extrinsic(self, block: Block, extrinsic_index: ExtrinsicIndex) -> Extrinsic | None: ...

    async def get_revealed_commitments(
        self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None
    ) -> list[RevealedCommitment] | None: ...

    async def get_all_revealed_commitments(self, netuid: NetUid, block: Block) -> SubnetRevealedCommitments: ...

    async def set_revealed_commitment(
        self, netuid: NetUid, commitment: RevealedCommitmentData, block_to_reveal: int, block_time: int | float
    ) -> int: ...

    async def get_drand_last_stored_round(self, block: Block | None = None) -> int: ...


class TurboBtContact(AbstractBittensorContact):
    def __init__(self, wallet: Wallet | None, uri: BittensorNetwork):
        super().__init__(wallet, uri)
        self._raw_client: Bittensor | None = None
        self._is_client_ready = asyncio.Event()

    async def _get_bt_client(self) -> Bittensor:
        if self._raw_client is None:
            raise AttributeError("The contact is not open.")
        async with asyncio.timeout(5):
            await self._is_client_ready.wait()
        return self._raw_client

    async def open(self) -> None:
        assert self._raw_client is None, "The contact is already open."
        logger.info("Opening the TurboBtContact for %s", self.uri)
        self._raw_client = Bittensor(wallet=self.wallet, uri=self.uri)
        await asyncio.shield(self._raw_client.__aenter__())
        self._is_client_ready.set()

    async def close(self) -> None:
        logger.info("Closing the TurboBtContact for %s", self.uri)
        assert self._raw_client is not None, "The contact is already closed."
        async with asyncio.timeout(5):
            await self._is_client_ready.wait()
        raw_client = self._raw_client
        self._raw_client = None
        self._is_client_ready.clear()
        await asyncio.shield(raw_client.__aexit__(None, None, None))

    async def _recreate_bt_client(self) -> None:
        assert self._raw_client is not None, "The contact is None so cannot be recreated."
        logger.info("Recreating Bittensor contact for %s", self.uri)
        if not self._is_client_ready.is_set():
            async with asyncio.timeout(5):
                await self._is_client_ready.wait()
            return
        self._is_client_ready.clear()
        try:
            old_client = self._raw_client
            try:
                await asyncio.shield(old_client.__aexit__(None, None, None))
            except Exception as exc:
                logger.warning(
                    "Failed to close old Bittensor contact during recreation for %s: %s",
                    self.uri,
                    self._transport_gist(exc),
                )
            self._raw_client = Bittensor(wallet=self.wallet, uri=self.uri)
            await asyncio.shield(self._raw_client.__aenter__())
        finally:
            self._is_client_ready.set()

    def _transport_gist(self, exc: BaseException) -> str:
        message = str(exc).strip()
        return f"{type(exc).__name__}: {message}" if message else type(exc).__name__

    def _transport_error(self, operation_name: str, exc: BaseException) -> BittensorTransportError:
        return BittensorTransportError(operation=operation_name, uri=str(self.uri), original_exception=exc)

    async def _protect_turbobt[T](self, operation_name: str, coro_factory: Callable[[Bittensor], Awaitable[T]]) -> T:
        bt_client = await self._get_bt_client()
        try:
            return await asyncio.shield(coro_factory(bt_client))
        except asyncio.CancelledError as cancelled_error:
            logger.info("Bittensor operation %s cancelled on %s; recreating contact", operation_name, self.uri)
            try:
                await asyncio.shield(self._recreate_bt_client())
            except asyncio.CancelledError:
                logger.info(
                    "Contact recreation cancelled while handling cancellation for %s on %s",
                    operation_name,
                    self.uri,
                )
            except Exception as exc:
                logger.warning(
                    "Contact recreation failed while handling cancellation for %s on %s: %s",
                    operation_name,
                    self.uri,
                    self._transport_gist(exc),
                )
            raise cancelled_error from None
        except RECONNECT_EXCEPTIONS as exc:
            logger.info(
                "Recoverable transport error during %s on %s: %s; recreating contact",
                operation_name,
                self.uri,
                self._transport_gist(exc),
            )
            try:
                await asyncio.shield(self._recreate_bt_client())
            except Exception as recreate_exc:
                raise self._transport_error(operation_name, recreate_exc) from recreate_exc
            bt_client = await self._get_bt_client()
            try:
                return await asyncio.shield(coro_factory(bt_client))
            except RECONNECT_EXCEPTIONS as retry_exc:
                raise self._transport_error(operation_name, retry_exc) from retry_exc

    def _resolve_hotkey(self, hotkey: Hotkey | None) -> Hotkey:
        if hotkey:
            return hotkey
        if self.wallet is None:
            raise ValueError("No hotkey provided while the contact has no wallet.")
        return Hotkey(self.wallet.hotkey.ss58_address)

    @track_operation(
        bittensor_operation_duration,
        labels={"uri": Attr("uri"), "hotkey": Attr("hotkey")},
    )
    async def get_block(self, number: BlockNumber) -> Block | None:
        block_obj = await self._protect_turbobt("get_block", lambda c: c.block(number).get())
        if block_obj is None or block_obj.number is None or block_obj.hash is None:
            return None
        return Block(number=BlockNumber(block_obj.number), hash=BlockHash(block_obj.hash))

    @track_operation(
        bittensor_operation_duration,
        labels={"uri": Attr("uri"), "hotkey": Attr("hotkey")},
    )
    async def get_latest_block(self) -> Block:
        block = await self.get_block(BlockNumber(LATEST_BLOCK_MARK))
        assert block is not None, "Latest block should always exist"
        return block

    async def get_block_timestamp(self, block: Block) -> Timestamp:
        async def _get_timestamp(bt_client: Bittensor):
            turbobt_block: TurboBtBlock = await bt_client.block(block.number).get()
            return await turbobt_block.get_timestamp()

        timestamp = await self._protect_turbobt("get_block_timestamp", _get_timestamp)
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
        labels={"uri": Attr("uri"), "netuid": Param("netuid"), "hotkey": Attr("hotkey")},
    )
    async def get_neurons_list(self, netuid: NetUid, block: Block) -> list[Neuron]:
        neurons = await self._protect_turbobt(
            "get_neurons_list", lambda c: c.subnet(netuid).list_neurons(block_hash=block.hash)
        )
        state = await self.get_subnet_state(netuid, block)
        stakes = state.hotkeys_stakes
        return [await self._translate_neuron(neuron, stakes[Hotkey(neuron.hotkey)]) for neuron in neurons]

    @track_operation(
        bittensor_operation_duration,
        labels={"uri": Attr("uri"), "netuid": Param("netuid"), "hotkey": Attr("hotkey")},
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
        labels={"uri": Attr("uri"), "netuid": Param("netuid"), "hotkey": Attr("hotkey")},
    )
    async def get_hyperparams(self, netuid: NetUid, block: Block) -> SubnetHyperparams | None:
        params = await self._protect_turbobt(
            "get_hyperparams", lambda c: c.subnet(netuid).get_hyperparameters(block_hash=block.hash)
        )
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
        labels={"uri": Attr("uri"), "netuid": Param("netuid"), "hotkey": Attr("hotkey")},
    )
    async def get_certificates(self, netuid: NetUid, block: Block) -> dict[Hotkey, NeuronCertificate]:
        certificates = await self._protect_turbobt(
            "get_certificates", lambda c: c.subnet(netuid).neurons.get_certificates(block_hash=block.hash)
        )
        if not certificates:
            return {}
        return {
            Hotkey(hotkey): await self._translate_certificate(certificate)
            for hotkey, certificate in certificates.items()
        }

    @track_operation(
        bittensor_operation_duration,
        labels={"uri": Attr("uri"), "netuid": Param("netuid"), "hotkey": Attr("hotkey")},
    )
    async def get_certificate(
        self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None
    ) -> NeuronCertificate | None:
        resolved_hotkey = self._resolve_hotkey(hotkey)
        certificate = await self._protect_turbobt(
            "get_certificate",
            lambda c: c.subnet(netuid).neuron(hotkey=resolved_hotkey).get_certificate(block_hash=block.hash),
        )
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
        labels={"uri": Attr("uri"), "netuid": Param("netuid"), "hotkey": Attr("hotkey")},
    )
    async def generate_certificate_keypair(
        self, netuid: NetUid, algorithm: CertificateAlgorithm
    ) -> NeuronCertificateKeypair | None:
        keypair = await self._protect_turbobt(
            "generate_certificate_keypair",
            lambda c: c.subnet(netuid).neurons.generate_certificate_keypair(
                algorithm=TurboBtCertificateAlgorithm(algorithm)
            ),
        )
        if keypair:
            keypair = await self._translate_certificate_keypair(keypair)
        return keypair

    @track_operation(
        bittensor_operation_duration,
        labels={"uri": Attr("uri"), "netuid": Param("netuid"), "hotkey": Attr("hotkey")},
    )
    async def get_subnet_state(self, netuid: NetUid, block: Block) -> SubnetState:
        state = await self._protect_turbobt("get_subnet_state", lambda c: c.subnet(netuid).get_state(block.hash))
        return SubnetState(**state)  # type: ignore[arg-type]

    @track_operation(
        bittensor_operation_duration,
        labels={"uri": Attr("uri"), "netuid": Param("netuid"), "hotkey": Attr("hotkey")},
    )
    async def commit_weights(self, netuid: NetUid, weights: dict[NeuronUid, Weight]) -> RevealRound:
        normalized_weights = {int(uid): float(weight) for uid, weight in weights.items()}
        reveal_round = await self._protect_turbobt(
            "commit_weights", lambda c: c.subnet(netuid).weights.commit(normalized_weights)
        )
        return RevealRound(reveal_round)

    @track_operation(
        bittensor_operation_duration,
        labels={"uri": Attr("uri"), "netuid": Param("netuid"), "hotkey": Attr("hotkey")},
    )
    async def set_weights(self, netuid: NetUid, weights: dict[NeuronUid, Weight]) -> None:
        normalized_weights = {int(uid): float(weight) for uid, weight in weights.items()}
        await self._protect_turbobt("set_weights", lambda c: c.subnet(netuid).weights.set(normalized_weights))

    @track_operation(
        bittensor_operation_duration,
        labels={"uri": Attr("uri"), "netuid": Param("netuid"), "hotkey": Attr("hotkey")},
    )
    async def get_commitment(
        self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None
    ) -> CommitmentVariant | None:
        resolved_hotkey = self._resolve_hotkey(hotkey)
        result = await self._protect_turbobt(
            "get_commitment", lambda c: c.subnet(netuid).commitments.get(resolved_hotkey, block_hash=block.hash)
        )
        if result is None:
            return None
        return map_to_commitment(result, resolved_hotkey)

    @track_operation(
        bittensor_operation_duration,
        labels={"uri": Attr("uri"), "netuid": Param("netuid"), "hotkey": Attr("hotkey")},
    )
    async def get_revealed_commitments(
        self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None
    ) -> list[RevealedCommitment] | None:
        resolved_hotkey = self._resolve_hotkey(hotkey)
        raw_commitments = await self._protect_turbobt(
            "get_revealed_commitments",
            lambda c: c.subnet(netuid).commitments.get_revealed(resolved_hotkey, block_hash=block.hash),
        )
        if raw_commitments is None:
            return None
        return [map_to_revealed_commitment(result, resolved_hotkey) for result in raw_commitments]

    @track_operation(
        bittensor_operation_duration,
        labels={"uri": Attr("uri"), "netuid": Param("netuid"), "hotkey": Attr("hotkey")},
    )
    async def get_commitments(self, netuid: NetUid, block: Block) -> SubnetCommitments:
        raw_commitments = await self._protect_turbobt(
            "get_commitments", lambda c: c.subnet(netuid).commitments.fetch(block_hash=block.hash)
        )
        commitments = {
            Hotkey(hotkey_str): map_to_commitment(result, Hotkey(hotkey_str))
            for hotkey_str, result in raw_commitments.items()
        }
        return SubnetCommitments(block=block, commitments=commitments)

    @track_operation(
        bittensor_operation_duration,
        labels={"uri": Attr("uri"), "netuid": Param("netuid"), "hotkey": Attr("hotkey")},
    )
    async def get_all_revealed_commitments(self, netuid: NetUid, block: Block) -> SubnetRevealedCommitments:
        raw_commitments = await self._protect_turbobt(
            "get_revealed_commitments", lambda c: c.subnet(netuid).commitments.fetch_revealed(block_hash=block.hash)
        )
        commitments: dict[Hotkey, list[RevealedCommitment]] = {}
        for hotkey_str, results in raw_commitments.items():
            hotkey = Hotkey(hotkey_str)
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
    async def set_revealed_commitment(
        self, netuid: NetUid, commitment: RevealedCommitmentData, block_to_reveal: int, block_time: int | float
    ) -> int:
        return await self._protect_turbobt(
            "set_revealed_commitment",
            lambda c: c.subnet(netuid).commitments.set_revealed(commitment, block_to_reveal, block_time),
        )

    @track_operation(
        bittensor_operation_duration,
        labels={"uri": Attr("uri"), "hotkey": Attr("hotkey")},
    )
    async def get_drand_last_stored_round(self, block: Block | None = None) -> int:
        logger.debug(f"Fetching last stored drand round at {self.uri}")
        return await self._protect_turbobt(
            "get_drand_last_stored_round",
            lambda c: c.drand.get_last_stored_round(block.hash if block else None),
        )

    @track_operation(
        bittensor_operation_duration,
        labels={"uri": Attr("uri"), "netuid": Param("netuid"), "hotkey": Attr("hotkey")},
    )
    async def set_commitment(self, netuid: NetUid, data: CommitmentDataBytes) -> None:
        await self._protect_turbobt("set_commitment", lambda c: c.subnet(netuid).commitments.set(bytes(data)))

    async def get_signed_block(self, block: Block) -> SignedBlock | None:
        return await self._protect_turbobt("get_signed_block", lambda c: c.subtensor.chain.getBlock(block.hash))

    async def get_extrinsic(self, block: Block, extrinsic_index: ExtrinsicIndex) -> Extrinsic | None:
        signed_block = await self.get_signed_block(block)
        if signed_block is None:
            return None

        extrinsics: list[TurboBtExtrinsic] = signed_block["block"]["extrinsics"]  # type: ignore[assignment]
        if extrinsic_index >= len(extrinsics):
            return None

        raw_extrinsic = extrinsics[extrinsic_index]
        return self._translate_extrinsic(raw_extrinsic, block.number, extrinsic_index)

    @staticmethod
    def _translate_extrinsic(
        raw_extrinsic: TurboBtExtrinsic, block_number: BlockNumber, extrinsic_index: ExtrinsicIndex
    ) -> Extrinsic:
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


@dataclass(slots=True)
class ContactFactory:
    contact_cls: type[AbstractBittensorContact] = TurboBtContact

    def create(self, wallet: Wallet | None, uri: BittensorNetwork) -> AbstractBittensorContact:
        return self.contact_cls(wallet=wallet, uri=uri)
