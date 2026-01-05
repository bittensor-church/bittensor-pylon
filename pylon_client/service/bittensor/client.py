from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import Any, Generic, TypeVar

from bittensor_wallet import Wallet
from turbobt.block import Block as TurboBtBlock
from turbobt.client import Bittensor
from turbobt.neuron import Neuron as TurboBtNeuron
from turbobt.subnet import CertificateAlgorithm as TurboBtCertificateAlgorithm
from turbobt.subnet import (
    NeuronCertificate as TurboBtNeuronCertificate,
)
from turbobt.subnet import (
    NeuronCertificateKeypair as TurboBtNeuronCertificateKeypair,
)
from turbobt.subnet import (
    SubnetHyperparams as TurboBtSubnetHyperparams,
)
from turbobt.substrate.exceptions import UnknownBlock

from pylon_client._internal.common.constants import LATEST_BLOCK_MARK
from pylon_client._internal.common.currency import Currency, Token
from pylon_client._internal.common.models import (
    AxonInfo,
    AxonProtocol,
    Block,
    CertificateAlgorithm,
    Commitment,
    CommitReveal,
    Neuron,
    NeuronCertificate,
    NeuronCertificateKeypair,
    Stakes,
    SubnetCommitments,
    SubnetHyperparams,
    SubnetNeurons,
    SubnetState,
    SubnetValidators,
)
from pylon_client._internal.common.types import (
    ArchiveBlocksCutoff,
    BittensorNetwork,
    BlockHash,
    BlockNumber,
    Coldkey,
    CommitmentDataBytes,
    Consensus,
    Dividends,
    Emission,
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
from pylon_client.service.metrics import (
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
    async def get_commitment(self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None) -> Commitment | None:
        """
        Fetches commitment data for a hotkey in a subnet. If no hotkey is provided, the hotkey of the client's wallet
        is used.
        """

    @abstractmethod
    async def get_commitments(self, netuid: NetUid, block: Block) -> SubnetCommitments:
        """
        Fetches all commitments for a subnet.
        """

    @abstractmethod
    async def set_commitment(self, netuid: NetUid, data: CommitmentDataBytes) -> None:
        """
        Sets commitment data on chain for the wallet's hotkey.
        """

    @abstractmethod
    async def get_validators(self, netuid: NetUid, block: Block) -> SubnetValidators:
        """
        Fetches validators (neurons with validator_permit=True) at the given block,
        sorted by total stake in descending order.
        """


class TurboBtClient(AbstractBittensorClient):
    """
    Adapter for turbobt client.
    """

    def __init__(self, wallet: Wallet | None, uri: BittensorNetwork):
        super().__init__(wallet, uri)
        self._raw_client: Bittensor | None = None

    async def open(self) -> None:
        assert self._raw_client is None, "The client is already open."
        logger.info(f"Opening the TurboBtClient for {self.uri}")
        self._raw_client = Bittensor(wallet=self.wallet, uri=self.uri)
        await self._raw_client.__aenter__()

    async def close(self) -> None:
        assert self._raw_client is not None, "The client is already closed."
        logger.info(f"Closing the TurboBtClient for {self.uri}")
        await self._raw_client.__aexit__(None, None, None)
        self._raw_client = None

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
        assert self._raw_client is not None, (
            "The client is not open, please use the client as a context manager or call the open() method."
        )
        logger.debug(f"Fetching the block with number {number} from {self.uri}")
        block_obj = await self._raw_client.block(number).get()
        if block_obj is None or block_obj.number is None:
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
        assert self._raw_client is not None, (
            "The client is not open, please use the client as a context manager or call the open() method."
        )
        turbobt_block: TurboBtBlock = await self._raw_client.block(block.number).get()
        timestamp = await turbobt_block.get_timestamp()
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
        assert self._raw_client is not None, (
            "The client is not open, please use the client as a context manager or call the open() method."
        )
        logger.debug(f"Fetching neurons from subnet {netuid} at block {block.number}, {self.uri}")
        neurons = await self._raw_client.subnet(netuid).list_neurons(block_hash=block.hash)
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
        assert self._raw_client is not None, (
            "The client is not open, please use the client as a context manager or call the open() method."
        )
        logger.debug(f"Fetching hyperparams from subnet {netuid} at block {block.number}, {self.uri}")
        params = await self._raw_client.subnet(netuid).get_hyperparameters(block_hash=block.hash)
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
        assert self._raw_client is not None, (
            "The client is not open, please use the client as a context manager or call the open() method."
        )
        logger.debug(f"Fetching certificates from subnet {netuid} at block {block.number}, {self.uri}")
        certificates = await self._raw_client.subnet(netuid).neurons.get_certificates(block_hash=block.hash)
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
        assert self._raw_client is not None, (
            "The client is not open, please use the client as a context manager or call the open() method."
        )
        hotkey = self._resolve_hotkey(hotkey)
        logger.debug(
            f"Fetching certificate of {hotkey} hotkey from subnet {netuid} at block {block.number}, {self.uri}"
        )
        certificate = await self._raw_client.subnet(netuid).neuron(hotkey=hotkey).get_certificate(block_hash=block.hash)
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
        assert self._raw_client is not None, (
            "The client is not open, please use the client as a context manager or call the open() method."
        )
        logger.debug(f"Generating certificate on subnet {netuid} at {self.uri}")
        keypair = await self._raw_client.subnet(netuid).neurons.generate_certificate_keypair(
            algorithm=TurboBtCertificateAlgorithm(algorithm)
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
        assert self._raw_client is not None, (
            "The client is not open, please use the client as a context manager or call the open() method."
        )
        logger.debug(f"Fetching subnet {netuid} state at block {block.number}, {self.uri}")
        state = await self._raw_client.subnet(netuid).get_state(block.hash)
        return SubnetState(**state)  # type: ignore

    async def _translate_weights(self, netuid: NetUid, weights: dict[Hotkey, Weight]) -> dict[int, float]:
        assert self._raw_client is not None, (
            "The client is not open, please use the client as a context manager or call the open() method."
        )
        translated_weights = {}
        missing = []
        latest_block = await self.get_latest_block()
        # We don't use self.get_neurons to avoid unnecessary call for subnet state, translation etc.
        neurons = await self._raw_client.subnet(netuid).list_neurons(block_hash=latest_block.hash)
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
        assert self._raw_client is not None, (
            "The client is not open, please use the client as a context manager or call the open() method."
        )
        logger.debug(f"Commiting weights on subnet {netuid} at {self.uri}")
        reveal_round = await self._raw_client.subnet(netuid).weights.commit(
            await self._translate_weights(netuid, weights)
        )
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
        assert self._raw_client is not None, (
            "The client is not open, please use the client as a context manager or call the open() method."
        )
        logger.debug(f"Setting weights on subnet {netuid} at {self.uri}")
        await self._raw_client.subnet(netuid).weights.set(await self._translate_weights(netuid, weights))

    @track_operation(
        bittensor_operation_duration,
        labels={
            "uri": Attr("uri"),
            "netuid": Param("netuid"),
            "hotkey": Attr("hotkey"),
        },
    )
    async def get_commitment(self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None) -> Commitment | None:
        assert self._raw_client is not None, (
            "The client is not open, please use the client as a context manager or call the open() method."
        )
        hotkey = self._resolve_hotkey(hotkey)
        logger.debug(f"Fetching commitment for {hotkey} from subnet {netuid} at block {block.number}, {self.uri}")
        commitment = await self._raw_client.subnet(netuid).commitments.get(hotkey, block_hash=block.hash)
        if commitment is None:
            return None
        return Commitment(block=block, hotkey=hotkey, commitment=CommitmentDataBytes(commitment).hex())

    @track_operation(
        bittensor_operation_duration,
        labels={
            "uri": Attr("uri"),
            "netuid": Param("netuid"),
            "hotkey": Attr("hotkey"),
        },
    )
    async def get_commitments(self, netuid: NetUid, block: Block) -> SubnetCommitments:
        assert self._raw_client is not None, (
            "The client is not open, please use the client as a context manager or call the open() method."
        )
        logger.debug(f"Fetching all commitments from subnet {netuid} at block {block.number}, {self.uri}")
        commitments = await self._raw_client.subnet(netuid).commitments.fetch(block_hash=block.hash)
        return SubnetCommitments(
            block=block,
            commitments={Hotkey(hotkey): CommitmentDataBytes(data).hex() for hotkey, data in commitments.items()},
        )

    @track_operation(
        bittensor_operation_duration,
        labels={
            "uri": Attr("uri"),
            "netuid": Param("netuid"),
            "hotkey": Attr("hotkey"),
        },
    )
    async def set_commitment(self, netuid: NetUid, data: CommitmentDataBytes) -> None:
        assert self._raw_client is not None, (
            "The client is not open, please use the client as a context manager or call the open() method."
        )
        logger.debug(f"Setting commitment on subnet {netuid} at {self.uri}")
        # Convert to plain bytes because scalecodec uses `type(value) is bytes` check
        # which fails for bytes subclasses like CommitmentDataBytes
        await self._raw_client.subnet(netuid).commitments.set(bytes(data))

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


SubClient = TypeVar("SubClient", bound=AbstractBittensorClient)
DelegateReturn = TypeVar("DelegateReturn")


class FallbackReason(StrEnum):
    STALE_BLOCK = "stale_block"
    UNKNOWN_BLOCK = "unknown_block"


class BittensorClient(Generic[SubClient], AbstractBittensorClient):
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

    async def get_commitment(self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None) -> Commitment | None:
        return await self._delegate(self.subclient_cls.get_commitment, netuid=netuid, block=block, hotkey=hotkey)

    async def get_commitments(self, netuid: NetUid, block: Block) -> SubnetCommitments:
        return await self._delegate(self.subclient_cls.get_commitments, netuid=netuid, block=block)

    async def set_commitment(self, netuid: NetUid, data: CommitmentDataBytes) -> None:
        return await self._delegate(self.subclient_cls.set_commitment, netuid=netuid, data=data)

    async def get_validators(self, netuid: NetUid, block: Block) -> SubnetValidators:
        return await self._delegate(self.subclient_cls.get_validators, netuid=netuid, block=block)

    async def _delegate(
        self, operation: Callable[..., Awaitable[DelegateReturn]], *args, block: Block | None = None, **kwargs
    ) -> DelegateReturn:
        """
        Execute operation with a proper client.

        Operations that does not need a block are executed by the main client.
        Archive client is used when the block is stale (older than archive_blocks_cutoff blocks).
        Operations on the main client are retried if UnknownBlock exception is raised.
        """
        operation_name = operation.__name__

        if block:
            kwargs["block"] = block
            latest_block = await self._main_client.get_latest_block()
            if latest_block.number - block.number > self._archive_blocks_cutoff:
                logger.debug(f"Block is stale, falling back to the archive client: {self._archive_client.uri}")
                bittensor_fallback_total.labels(
                    reason=FallbackReason.STALE_BLOCK,
                    operation=operation_name,
                    hotkey=self.hotkey,
                ).inc()
                return await operation(self._archive_client, *args, **kwargs)

        try:
            return await operation(self._main_client, *args, **kwargs)
        except UnknownBlock:
            logger.warning(
                f"Block unknown for the main client, falling back to the archive client: {self._archive_client.uri}"
            )
            bittensor_fallback_total.labels(
                reason=FallbackReason.UNKNOWN_BLOCK,
                operation=operation_name,
                hotkey=self.hotkey,
            ).inc()
            return await operation(self._archive_client, *args, **kwargs)
