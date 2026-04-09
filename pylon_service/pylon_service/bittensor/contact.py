from __future__ import annotations

import asyncio
import inspect
import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Protocol

from bittensor_wallet import Wallet
from pylon_commons.constants import LATEST_BLOCK_MARK
from pylon_commons.currency import Currency, Token
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

from pylon_service.bittensor.models import (
    AxonInfo,
    AxonProtocol,
    Block,
    CertificateAlgorithm,
    Commitment,
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
from pylon_service.metrics import Attr, Param, bittensor_operation_duration, track_operation
from tests.behave import Behave, Behavior

logger = logging.getLogger(__name__)

unknown_hotkey = Hotkey("N/A")


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
    async def get_commitment(self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None) -> Commitment | None: ...

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
    async def get_commitment(self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None) -> Commitment | None: ...
    async def get_commitments(self, netuid: NetUid, block: Block) -> SubnetCommitments: ...
    async def set_commitment(self, netuid: NetUid, data: CommitmentDataBytes) -> None: ...
    async def get_signed_block(self, block: Block) -> SignedBlock | None: ...
    async def get_extrinsic(self, block: Block, extrinsic_index: ExtrinsicIndex) -> Extrinsic | None: ...


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
        logger.warning("Recreating Bittensor contact for %s", self.uri)
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
                logger.warning("Failed to close old Bittensor contact during recreation", exc_info=True)
            self._raw_client = Bittensor(wallet=self.wallet, uri=self.uri)
            await asyncio.shield(self._raw_client.__aenter__())
        finally:
            self._is_client_ready.set()

    async def _protect_turbobt[T](self, coro_factory: Callable[[Bittensor], Awaitable[T]]) -> T:
        bt_client = await self._get_bt_client()
        try:
            return await asyncio.shield(coro_factory(bt_client))
        except asyncio.CancelledError as cancelled_error:
            logger.warning("Cancellation caught during bittensor operation on %s, recreating contact", self.uri)
            try:
                await asyncio.shield(self._recreate_bt_client())
            except asyncio.CancelledError:
                logger.warning("Recreation was cancelled during cancellation handling on %s", self.uri)
            except Exception:
                logger.exception("Failed to recreate contact after cancellation on %s", self.uri)
            raise cancelled_error from None
        except (ConnectionClosed, RuntimeError):
            logger.exception(
                "Transport/runtime error caught during bittensor operation on %s, recreating contact", self.uri
            )
            await asyncio.shield(self._recreate_bt_client())
            bt_client = await self._get_bt_client()
            return await asyncio.shield(coro_factory(bt_client))

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
        block_obj = await self._protect_turbobt(lambda c: c.block(number).get())
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

        timestamp = await self._protect_turbobt(_get_timestamp)
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
        neurons = await self._protect_turbobt(lambda c: c.subnet(netuid).list_neurons(block_hash=block.hash))
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
        params = await self._protect_turbobt(lambda c: c.subnet(netuid).get_hyperparameters(block_hash=block.hash))
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
            lambda c: c.subnet(netuid).neurons.get_certificates(block_hash=block.hash)
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
            lambda c: c.subnet(netuid).neuron(hotkey=resolved_hotkey).get_certificate(block_hash=block.hash)
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
            lambda c: c.subnet(netuid).neurons.generate_certificate_keypair(
                algorithm=TurboBtCertificateAlgorithm(algorithm)
            )
        )
        if keypair:
            keypair = await self._translate_certificate_keypair(keypair)
        return keypair

    @track_operation(
        bittensor_operation_duration,
        labels={"uri": Attr("uri"), "netuid": Param("netuid"), "hotkey": Attr("hotkey")},
    )
    async def get_subnet_state(self, netuid: NetUid, block: Block) -> SubnetState:
        state = await self._protect_turbobt(lambda c: c.subnet(netuid).get_state(block.hash))
        return SubnetState(**state)  # type: ignore[arg-type]

    @track_operation(
        bittensor_operation_duration,
        labels={"uri": Attr("uri"), "netuid": Param("netuid"), "hotkey": Attr("hotkey")},
    )
    async def commit_weights(self, netuid: NetUid, weights: dict[NeuronUid, Weight]) -> RevealRound:
        normalized_weights = {int(uid): float(weight) for uid, weight in weights.items()}
        reveal_round = await self._protect_turbobt(lambda c: c.subnet(netuid).weights.commit(normalized_weights))
        return RevealRound(reveal_round)

    @track_operation(
        bittensor_operation_duration,
        labels={"uri": Attr("uri"), "netuid": Param("netuid"), "hotkey": Attr("hotkey")},
    )
    async def set_weights(self, netuid: NetUid, weights: dict[NeuronUid, Weight]) -> None:
        normalized_weights = {int(uid): float(weight) for uid, weight in weights.items()}
        await self._protect_turbobt(lambda c: c.subnet(netuid).weights.set(normalized_weights))

    @track_operation(
        bittensor_operation_duration,
        labels={"uri": Attr("uri"), "netuid": Param("netuid"), "hotkey": Attr("hotkey")},
    )
    async def get_commitment(self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None) -> Commitment | None:
        resolved_hotkey = self._resolve_hotkey(hotkey)
        result = await self._protect_turbobt(
            lambda c: c.subnet(netuid).commitments.get(resolved_hotkey, block_hash=block.hash)
        )
        if result is None:
            return None
        return Commitment(
            commitment_block_number=BlockNumber(result["block"]),
            hotkey=resolved_hotkey,
            commitment=CommitmentDataBytes(result["data"]).hex(),
        )

    @track_operation(
        bittensor_operation_duration,
        labels={"uri": Attr("uri"), "netuid": Param("netuid"), "hotkey": Attr("hotkey")},
    )
    async def get_commitments(self, netuid: NetUid, block: Block) -> SubnetCommitments:
        raw_commitments = await self._protect_turbobt(
            lambda c: c.subnet(netuid).commitments.fetch(block_hash=block.hash)
        )
        commitments = {
            Hotkey(hotkey): Commitment(
                commitment_block_number=BlockNumber(result["block"]),
                hotkey=Hotkey(hotkey),
                commitment=CommitmentDataBytes(result["data"]).hex(),
            )
            for hotkey, result in raw_commitments.items()
        }
        return SubnetCommitments(block=block, commitments=commitments)

    @track_operation(
        bittensor_operation_duration,
        labels={"uri": Attr("uri"), "netuid": Param("netuid"), "hotkey": Attr("hotkey")},
    )
    async def set_commitment(self, netuid: NetUid, data: CommitmentDataBytes) -> None:
        await self._protect_turbobt(lambda c: c.subnet(netuid).commitments.set(bytes(data)))

    async def get_signed_block(self, block: Block) -> SignedBlock | None:
        return await self._protect_turbobt(lambda c: c.subtensor.chain.getBlock(block.hash))

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


class MockBittensorContact(AbstractBittensorContact):
    def __init__(self, wallet: Any | None = None, uri: BittensorNetwork = BittensorNetwork("mock://test")):
        super().__init__(wallet=wallet, uri=uri)
        self._behave = Behave()
        self._is_open = False
        self._defaults: dict[str, Behavior] = {}

    async def open(self) -> None:
        self._is_open = True

    async def close(self) -> None:
        self._is_open = False

    @asynccontextmanager
    async def mock_behavior(self, **behaviors: list[Behavior] | Behavior):
        async with self._behave.mock(**behaviors):
            yield

    def add_behavior(self, method_name: str, behavior: Behavior) -> None:
        self._behave.add_behavior(method_name, behavior)

    def set_default(self, method_name: str, behavior: Behavior) -> None:
        self._defaults[method_name] = behavior

    def reset(self) -> None:
        self._behave.reset()
        self._defaults.clear()

    @property
    def calls(self):
        return self._behave.calls

    async def _execute_behavior(self, method_name: str, *args, **kwargs) -> Any:
        self._behave.track(method_name, *args, **kwargs)
        try:
            return await self._behave.execute(method_name, *args, **kwargs)
        except NotImplementedError:
            if method_name not in self._defaults:
                raise

        behavior = self._defaults[method_name]
        if isinstance(behavior, Exception):
            raise behavior
        if callable(behavior):
            result = behavior(*args, **kwargs)
            if inspect.iscoroutine(result):
                return await result
            return result
        return behavior

    async def get_block(self, number: BlockNumber) -> Block | None:
        return await self._execute_behavior("get_block", number)

    async def get_latest_block(self) -> Block:
        return await self._execute_behavior("get_latest_block")

    async def get_block_timestamp(self, block: Block) -> Timestamp:
        return await self._execute_behavior("get_block_timestamp", block)

    async def get_neurons_list(self, netuid: NetUid, block: Block) -> list[Neuron]:
        return await self._execute_behavior("get_neurons_list", netuid, block)

    async def get_hyperparams(self, netuid: NetUid, block: Block) -> SubnetHyperparams | None:
        return await self._execute_behavior("get_hyperparams", netuid, block)

    async def get_certificates(self, netuid: NetUid, block: Block) -> dict[Hotkey, NeuronCertificate]:
        return await self._execute_behavior("get_certificates", netuid, block)

    async def get_certificate(
        self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None
    ) -> NeuronCertificate | None:
        return await self._execute_behavior("get_certificate", netuid, block, hotkey)

    async def generate_certificate_keypair(
        self, netuid: NetUid, algorithm: CertificateAlgorithm
    ) -> NeuronCertificateKeypair | None:
        return await self._execute_behavior("generate_certificate_keypair", netuid, algorithm)

    async def get_subnet_state(self, netuid: NetUid, block: Block) -> SubnetState:
        return await self._execute_behavior("get_subnet_state", netuid, block)

    async def commit_weights(self, netuid: NetUid, weights: dict[NeuronUid, Weight]) -> RevealRound:
        return await self._execute_behavior("commit_weights", netuid, weights)

    async def set_weights(self, netuid: NetUid, weights: dict[NeuronUid, Weight]) -> None:
        return await self._execute_behavior("set_weights", netuid, weights)

    async def get_neurons(self, netuid: NetUid, block: Block) -> SubnetNeurons:
        return await self._execute_behavior("get_neurons", netuid, block)

    async def get_commitment(self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None) -> Commitment | None:
        return await self._execute_behavior("get_commitment", netuid, block, hotkey)

    async def get_commitments(self, netuid: NetUid, block: Block) -> SubnetCommitments:
        return await self._execute_behavior("get_commitments", netuid, block)

    async def set_commitment(self, netuid: NetUid, data: CommitmentDataBytes) -> None:
        return await self._execute_behavior("set_commitment", netuid, data)

    async def get_signed_block(self, block: Block) -> SignedBlock | None:
        return await self._execute_behavior("get_signed_block", block)

    async def get_extrinsic(self, block: Block, extrinsic_index: ExtrinsicIndex) -> Extrinsic | None:
        return await self._execute_behavior("get_extrinsic", block, extrinsic_index)


@dataclass(slots=True)
class ContactFactory:
    contact_cls: type[AbstractBittensorContact] = TurboBtContact

    def create(self, wallet: Wallet | None, uri: BittensorNetwork) -> AbstractBittensorContact:
        return self.contact_cls(wallet=wallet, uri=uri)
