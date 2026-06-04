from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from bittensor_wallet import Wallet
from pylon_commons.models import CommitmentVariant, RevealedCommitment, SubnetRevealedCommitments
from pylon_commons.types import (
    ArchiveBlocksCutoff,
    CommitmentDataBytes,
    ExtrinsicIndex,
    Hotkey,
    MechanismId,
    NetUid,
    NeuronUid,
    RevealedCommitmentData,
    Weight,
)
from turbobt.substrate.exceptions import UnknownBlock

from pylon_service.bittensor.contact import AbstractBittensorContact
from pylon_service.bittensor.exceptions import ArchiveFallbackException
from pylon_service.bittensor.models import (
    Block,
    CertificateAlgorithm,
    Extrinsic,
    Neuron,
    NeuronCertificate,
    NeuronCertificateKeypair,
    SubnetCommitments,
    SubnetHyperparams,
    SubnetNeurons,
    SubnetPrice,
    SubnetPrices,
    SubnetState,
)
from pylon_service.metrics import bittensor_fallback_total

logger = logging.getLogger(__name__)


class BittensorContactRouter:
    """
    Wallet-bound facade that exposes the contact interface while routing stale-block reads to archive.
    """

    def __init__(
        self,
        wallet: Wallet | None,
        main_contact: AbstractBittensorContact,
        archive_contact: AbstractBittensorContact,
        archive_blocks_cutoff: ArchiveBlocksCutoff,
    ) -> None:
        self.wallet = wallet
        self.hotkey = main_contact.hotkey
        self.uri = main_contact.uri
        self.archive_uri = archive_contact.uri
        self._main_contact = main_contact
        self._archive_contact = archive_contact
        self._archive_blocks_cutoff = archive_blocks_cutoff

    async def open(self) -> None:
        await self._main_contact.open()
        await self._archive_contact.open()

    async def close(self) -> None:
        await self._main_contact.close()
        await self._archive_contact.close()

    async def __aenter__(self):
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _delegate[T](
        self,
        operation_name: str,
        main_call: Callable[[], Awaitable[T]],
        archive_call: Callable[[], Awaitable[T]],
        block: Block | None = None,
    ) -> T:
        if block is not None:
            latest_block = await self._main_contact.get_latest_block()
            if latest_block.number - block.number > self._archive_blocks_cutoff:
                logger.debug("Block %s is stale, using archive contact %s", block.number, self._archive_contact.uri)
                bittensor_fallback_total.labels(
                    reason="stale_block",
                    operation=operation_name,
                    hotkey=self.hotkey,
                ).inc()
                try:
                    return await archive_call()
                except UnknownBlock as exc:
                    raise ArchiveFallbackException(
                        detail=(
                            f"Block {block.number} data is unavailable on the archive node. "
                            f"Archive was used because the block exceeded archive block cutoff ({self._archive_blocks_cutoff} blocks)."
                        )
                    ) from exc

        try:
            return await main_call()
        except UnknownBlock:
            if block is None:
                raise
            logger.warning(
                "Block %s unknown on main contact, falling back to archive %s", block.number, self.archive_uri
            )
            bittensor_fallback_total.labels(
                reason="unknown_block",
                operation=operation_name,
                hotkey=self.hotkey,
            ).inc()
            try:
                return await archive_call()
            except UnknownBlock as archive_exc:
                raise ArchiveFallbackException(
                    detail=f"Block {block.number} data is unavailable on both main and archive nodes."
                ) from archive_exc

    async def get_block(self, number):
        return await self._delegate(
            "get_block",
            main_call=lambda: self._main_contact.get_block(number),
            archive_call=lambda: self._archive_contact.get_block(number),
        )

    async def get_latest_block(self):
        return await self._delegate(
            "get_latest_block",
            main_call=self._main_contact.get_latest_block,
            archive_call=self._archive_contact.get_latest_block,
        )

    async def get_block_timestamp(self, block: Block):
        return await self._delegate(
            "get_block_timestamp",
            main_call=lambda: self._main_contact.get_block_timestamp(block),
            archive_call=lambda: self._archive_contact.get_block_timestamp(block),
            block=block,
        )

    async def get_neurons_list(self, netuid: NetUid, block: Block) -> list[Neuron]:
        return await self._delegate(
            "get_neurons_list",
            main_call=lambda: self._main_contact.get_neurons_list(netuid, block),
            archive_call=lambda: self._archive_contact.get_neurons_list(netuid, block),
            block=block,
        )

    async def get_hyperparams(self, netuid: NetUid, block: Block) -> SubnetHyperparams | None:
        return await self._delegate(
            "get_hyperparams",
            main_call=lambda: self._main_contact.get_hyperparams(netuid, block),
            archive_call=lambda: self._archive_contact.get_hyperparams(netuid, block),
            block=block,
        )

    async def get_certificates(self, netuid: NetUid, block: Block) -> dict:
        return await self._delegate(
            "get_certificates",
            main_call=lambda: self._main_contact.get_certificates(netuid, block),
            archive_call=lambda: self._archive_contact.get_certificates(netuid, block),
            block=block,
        )

    async def get_certificate(self, netuid: NetUid, block: Block, hotkey=None) -> NeuronCertificate | None:
        return await self._delegate(
            "get_certificate",
            main_call=lambda: self._main_contact.get_certificate(netuid, block, hotkey),
            archive_call=lambda: self._archive_contact.get_certificate(netuid, block, hotkey),
            block=block,
        )

    async def generate_certificate_keypair(
        self, netuid: NetUid, algorithm: CertificateAlgorithm
    ) -> NeuronCertificateKeypair | None:
        return await self._delegate(
            "generate_certificate_keypair",
            main_call=lambda: self._main_contact.generate_certificate_keypair(netuid, algorithm),
            archive_call=lambda: self._archive_contact.generate_certificate_keypair(netuid, algorithm),
        )

    async def get_subnet_state(self, netuid: NetUid, block: Block) -> SubnetState | None:
        return await self._delegate(
            "get_subnet_state",
            main_call=lambda: self._main_contact.get_subnet_state(netuid, block),
            archive_call=lambda: self._archive_contact.get_subnet_state(netuid, block),
            block=block,
        )

    async def commit_weights(self, netuid: NetUid, mechanism_id: MechanismId, weights: dict[NeuronUid, Weight]):
        return await self._delegate(
            "commit_weights",
            main_call=lambda: self._main_contact.commit_weights(netuid, mechanism_id, weights),
            archive_call=lambda: self._archive_contact.commit_weights(netuid, mechanism_id, weights),
        )

    async def set_weights(self, netuid: NetUid, mechanism_id: MechanismId, weights: dict[NeuronUid, Weight]) -> None:
        return await self._delegate(
            "set_weights",
            main_call=lambda: self._main_contact.set_weights(netuid, mechanism_id, weights),
            archive_call=lambda: self._archive_contact.set_weights(netuid, mechanism_id, weights),
        )

    async def get_neurons(self, netuid: NetUid, block: Block) -> SubnetNeurons:
        return await self._delegate(
            "get_neurons",
            main_call=lambda: self._main_contact.get_neurons(netuid, block),
            archive_call=lambda: self._archive_contact.get_neurons(netuid, block),
            block=block,
        )

    async def get_alpha_prices(self, block: Block) -> SubnetPrices:
        return await self._delegate(
            "get_alpha_prices",
            main_call=lambda: self._main_contact.get_alpha_prices(block),
            archive_call=lambda: self._archive_contact.get_alpha_prices(block),
            block=block,
        )

    async def get_alpha_price(self, netuid: NetUid, block: Block) -> SubnetPrice:
        return await self._delegate(
            "get_alpha_price",
            main_call=lambda: self._main_contact.get_alpha_price(netuid, block),
            archive_call=lambda: self._archive_contact.get_alpha_price(netuid, block),
            block=block,
        )

    async def get_commitment(self, netuid: NetUid, block: Block, hotkey=None) -> CommitmentVariant | None:
        return await self._delegate(
            "get_commitment",
            main_call=lambda: self._main_contact.get_commitment(netuid, block, hotkey),
            archive_call=lambda: self._archive_contact.get_commitment(netuid, block, hotkey),
            block=block,
        )

    async def get_commitments(self, netuid: NetUid, block: Block) -> SubnetCommitments:
        return await self._delegate(
            "get_commitments",
            main_call=lambda: self._main_contact.get_commitments(netuid, block),
            archive_call=lambda: self._archive_contact.get_commitments(netuid, block),
            block=block,
        )

    async def set_commitment(self, netuid: NetUid, data: CommitmentDataBytes) -> None:
        return await self._delegate(
            "set_commitment",
            main_call=lambda: self._main_contact.set_commitment(netuid, data),
            archive_call=lambda: self._archive_contact.set_commitment(netuid, data),
        )

    async def get_extrinsic(self, block: Block, extrinsic_index: ExtrinsicIndex) -> Extrinsic | None:
        return await self._delegate(
            "get_extrinsic",
            main_call=lambda: self._main_contact.get_extrinsic(block, extrinsic_index),
            archive_call=lambda: self._archive_contact.get_extrinsic(block, extrinsic_index),
            block=block,
        )

    async def get_revealed_commitments(
        self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None
    ) -> list[RevealedCommitment] | None:
        return await self._delegate(
            "get_revealed_commitments",
            main_call=lambda: self._main_contact.get_revealed_commitments(netuid, block, hotkey),
            archive_call=lambda: self._archive_contact.get_revealed_commitments(netuid, block, hotkey),
            block=block,
        )

    async def get_all_revealed_commitments(self, netuid: NetUid, block: Block) -> SubnetRevealedCommitments:
        return await self._delegate(
            "get_all_revealed_commitments",
            main_call=lambda: self._main_contact.get_all_revealed_commitments(netuid, block),
            archive_call=lambda: self._archive_contact.get_all_revealed_commitments(netuid, block),
            block=block,
        )

    async def set_revealed_commitment(
        self, netuid: NetUid, commitment: RevealedCommitmentData, block_to_reveal: int
    ) -> int:
        return await self._delegate(
            "set_revealed_commitment",
            main_call=lambda: self._main_contact.set_revealed_commitment(netuid, commitment, block_to_reveal),
            archive_call=lambda: self._archive_contact.set_revealed_commitment(netuid, commitment, block_to_reveal),
        )

    async def get_drand_last_stored_round(self, block: Block | None = None) -> int:
        return await self._delegate(
            "get_drand_last_stored_round",
            main_call=lambda: self._main_contact.get_drand_last_stored_round(block),
            archive_call=lambda: self._archive_contact.get_drand_last_stored_round(block),
            block=block,
        )
