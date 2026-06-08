from pylon_commons.models import (
    BlockInfoBag,
    CommitmentVariant,
    EvmAssociation,
    Extrinsic,
    RevealedCommitment,
    SubnetCommitments,
    SubnetEvmAssociations,
    SubnetNeurons,
    SubnetPrice,
    SubnetPrices,
    SubnetRevealedCommitments,
    SubnetValidators,
    WeightsStatus,
)
from pylon_commons.types import (
    BlockNumber,
    CommitmentDataBytes,
    ExtrinsicIndex,
    Hotkey,
    MechanismId,
    NetUid,
    NeuronUid,
    RevealedCommitmentData,
    Weight,
)

from pylon_service.api._unstable.tasks import ApplyWeights, SetCommitment, SetRevealedCommitment
from pylon_service.api.epoch import get_epoch_containing_block, get_tempo_from_hyperparams
from pylon_service.api.services import (
    BaseService,
    BlockNotFoundError,
    CertificateGenerationFailedError,
    CertificateNotFoundError,
    CommitmentNotFoundError,
    ExtrinsicNotFoundError,
    RecentObjectMissingError,
    RecentObjectStaleError,
)
from pylon_service.bittensor.contact import BittensorPort
from pylon_service.bittensor.models import (
    Block,
    CertificateAlgorithm,
    NeuronCertificate,
    NeuronCertificateKeypair,
    RawEvmKeyAssociationInfo,
)
from pylon_service.bittensor.recent import RecentObjectMissing, RecentObjectProvider, RecentObjectStale
from pylon_service.db.weight_task import weight_task_submitted
from pylon_service.identities import Identity


class BlockService(BaseService):
    async def get_latest_block_info(self) -> BlockInfoBag:
        block = await self.contact_router.get_latest_block()
        timestamp = await self.contact_router.get_block_timestamp(block)
        return BlockInfoBag(number=block.number, hash=block.hash, timestamp=timestamp)

    async def get_extrinsic(self, block_number: BlockNumber, extrinsic_index: ExtrinsicIndex) -> Extrinsic:
        block = await self.contact_router.get_block(block_number)
        if block is None:
            raise BlockNotFoundError(f"Block {block_number} not found.")

        extrinsic = await self.contact_router.get_extrinsic(block, extrinsic_index)
        if extrinsic is None:
            raise ExtrinsicNotFoundError(f"Extrinsic {block_number}-{extrinsic_index} not found.")

        return extrinsic


class PriceService(BaseService):
    async def get_latest_prices(self) -> SubnetPrices:
        block = await self.contact_router.get_latest_block()
        return await self.contact_router.get_alpha_prices(block)

    async def get_prices(self, block_number: BlockNumber) -> SubnetPrices:
        block = await self.contact_router.get_block(block_number)
        if block is None:
            raise BlockNotFoundError(f"Block {block_number} not found.")
        return await self.contact_router.get_alpha_prices(block)

    async def get_latest_price(self, netuid: NetUid) -> SubnetPrice:
        block = await self.contact_router.get_latest_block()
        return await self.contact_router.get_alpha_price(netuid, block)

    async def get_price(self, netuid: NetUid, block_number: BlockNumber) -> SubnetPrice:
        block = await self.contact_router.get_block(block_number)
        if block is None:
            raise BlockNotFoundError(f"Block {block_number} not found.")
        return await self.contact_router.get_alpha_price(netuid, block)


class NeuronService(BaseService):
    async def get_neurons(self, netuid: NetUid, block_number: BlockNumber) -> SubnetNeurons:
        block = await self.contact_router.get_block(block_number)
        if block is None:
            raise BlockNotFoundError(f"Block {block_number} not found.")

        return await self.contact_router.get_neurons(netuid, block)

    async def get_latest_neurons(self, netuid: NetUid) -> SubnetNeurons:
        block = await self.contact_router.get_latest_block()
        return await self.contact_router.get_neurons(netuid, block)

    async def get_recent_neurons(self, recent_object_provider: RecentObjectProvider) -> SubnetNeurons:
        try:
            return await recent_object_provider.get(SubnetNeurons)
        except RecentObjectMissing as exc:
            raise RecentObjectMissingError(
                "Recent neurons data is not available. Cache update may not have finished "
                "yet or subnet may not be configured for caching recent objects."
            ) from exc
        except RecentObjectStale as exc:
            raise RecentObjectStaleError("Recent neurons data is stale. Cache update may be failing.") from exc

    async def get_validators(self, netuid: NetUid, block_number: BlockNumber) -> SubnetValidators:
        block = await self.contact_router.get_block(block_number)
        if block is None:
            raise BlockNotFoundError(f"Block {block_number} not found.")

        subnet_neurons = await self.contact_router.get_neurons(netuid, block)
        validators = [neuron for neuron in subnet_neurons.neurons.values() if neuron.validator_permit]
        validators.sort(key=lambda neuron: neuron.stakes.total, reverse=True)
        return SubnetValidators(block=block, validators=validators)

    async def get_latest_validators(self, netuid: NetUid) -> SubnetValidators:
        block = await self.contact_router.get_latest_block()
        subnet_neurons = await self.contact_router.get_neurons(netuid, block)
        validators = [neuron for neuron in subnet_neurons.neurons.values() if neuron.validator_permit]
        validators.sort(key=lambda neuron: neuron.stakes.total, reverse=True)
        return SubnetValidators(block=block, validators=validators)


class CertificateService(BaseService):
    async def get_certificates(self, netuid: NetUid) -> dict[Hotkey, NeuronCertificate]:
        block = await self.contact_router.get_latest_block()
        return await self.contact_router.get_certificates(netuid, block)

    async def get_certificate(self, netuid: NetUid, hotkey: Hotkey) -> NeuronCertificate:
        block = await self.contact_router.get_latest_block()
        certificate = await self.contact_router.get_certificate(netuid, block, hotkey=hotkey)
        if certificate is None:
            raise CertificateNotFoundError("Certificate not found or error fetching.")
        return certificate

    async def get_own_certificate(self, netuid: NetUid) -> NeuronCertificate:
        block = await self.contact_router.get_latest_block()
        certificate = await self.contact_router.get_certificate(netuid, block)
        if certificate is None:
            raise CertificateNotFoundError("Certificate not found or error fetching.")
        return certificate

    async def generate_certificate_keypair(
        self, netuid: NetUid, algorithm: CertificateAlgorithm
    ) -> NeuronCertificateKeypair:
        certificate_keypair = await self.contact_router.generate_certificate_keypair(netuid, algorithm)
        if certificate_keypair is None:
            raise CertificateGenerationFailedError("Could not generate certificate pair.")
        return certificate_keypair


class CommitmentService(BaseService):
    async def set_commitment(self, netuid: NetUid, data: CommitmentDataBytes) -> None:
        await SetCommitment(self.contact_router, netuid, data)()

    async def get_commitments(self, netuid: NetUid) -> SubnetCommitments:
        block = await self.contact_router.get_latest_block()

        raw_commitments = await self.contact_router.get_commitments(netuid, block)
        state = await self.contact_router.get_subnet_state(netuid, block)
        if state is None:
            raise RuntimeError(f"Subnet state is unavailable for netuid {netuid} at block {block.number}.")
        registered_hotkeys = set(state.hotkeys)
        filtered = {
            hotkey: commitment
            for hotkey, commitment in raw_commitments.commitments.items()
            if hotkey in registered_hotkeys
        }
        return SubnetCommitments(block=raw_commitments.block, commitments=filtered)

    async def get_commitment(self, netuid: NetUid, hotkey: Hotkey) -> tuple[Block, CommitmentVariant]:
        block = await self.contact_router.get_latest_block()
        commitment = await self.contact_router.get_commitment(netuid, block, hotkey=hotkey)
        if commitment is None:
            raise CommitmentNotFoundError("Commitment not found.")
        return block, commitment

    async def get_own_commitment(self, netuid: NetUid) -> tuple[Block, CommitmentVariant]:
        block = await self.contact_router.get_latest_block()
        commitment = await self.contact_router.get_commitment(netuid, block)
        if commitment is None:
            raise CommitmentNotFoundError("Commitment not found.")
        return block, commitment

    async def set_revealed_commitment(
        self, netuid: NetUid, commitment: RevealedCommitmentData, block_until_reveal: int
    ) -> int:
        return await SetRevealedCommitment(self.contact_router, netuid, commitment, block_until_reveal)()

    async def get_all_revealed_commitments(self, netuid: NetUid) -> SubnetRevealedCommitments:
        block = await self.contact_router.get_latest_block()
        return await self.contact_router.get_all_revealed_commitments(netuid, block)

    async def get_revealed_commitments(
        self, netuid: NetUid, hotkey: Hotkey | None = None
    ) -> tuple[Block, list[RevealedCommitment]]:
        block = await self.contact_router.get_latest_block()
        commitments = await self.contact_router.get_revealed_commitments(netuid, block, hotkey=hotkey)
        if commitments is None:
            raise CommitmentNotFoundError("Revealed commitments not found.")
        return block, commitments

    async def get_own_revealed_commitments(self, netuid: NetUid) -> tuple[Block, list[RevealedCommitment]]:
        block = await self.contact_router.get_latest_block()
        commitments = await self.contact_router.get_revealed_commitments(netuid, block)
        if commitments is None:
            raise CommitmentNotFoundError("Revealed commitments not found.")
        return block, commitments


class WeightService(BaseService):
    def __init__(self, identity: Identity, contact_router: BittensorPort) -> None:
        super().__init__(contact_router)
        self.identity = identity

    async def set_weights(self, netuid: NetUid, mechanism_id: MechanismId, weights: dict[Hotkey, Weight]):
        await ApplyWeights(self.identity, self.contact_router, weights, netuid, mechanism_id).schedule()

    async def get_weight_status(
        self, netuid: NetUid, mechanism_id: MechanismId, block_number: BlockNumber
    ) -> WeightsStatus:
        block = await self.contact_router.get_block(block_number)
        if block is None:
            raise BlockNotFoundError(f"Block {block_number} not found.")
        hyperparams = await self.contact_router.get_hyperparams(netuid, block)
        tempo = get_tempo_from_hyperparams(hyperparams)
        epoch = get_epoch_containing_block(block_number, netuid, tempo)
        task_submitted = await weight_task_submitted(self.identity, mechanism_id, epoch)
        return WeightsStatus(weights_submitted=task_submitted)


class DrandService(BaseService):
    async def get_drand_last_stored_round(self) -> int:
        return await self.contact_router.get_drand_last_stored_round()


class EvmAssociationService(BaseService):
    async def get_latest_associations(self, netuid: NetUid) -> SubnetEvmAssociations:
        block = await self.contact_router.get_latest_block()
        associations = await self.contact_router.get_evm_key_associations(netuid, block)
        state = await self.contact_router.get_subnet_state(netuid, block)
        if state is None:
            raise RuntimeError(f"Subnet state is unavailable for netuid {netuid} at block {block.number}.")

        def map_to_evm_association(raw_association: RawEvmKeyAssociationInfo, hotkey: Hotkey) -> EvmAssociation:
            return EvmAssociation(
                hotkey=hotkey,
                evm_address=raw_association.evm_address,
                last_block_where_ownership_was_proven=raw_association.last_block_where_ownership_was_proven,
            )

        return SubnetEvmAssociations(
            block=block,
            evm_associations={
                state.hotkeys[uid]: map_to_evm_association(associations[NeuronUid(uid)], state.hotkeys[uid])
                for uid in range(len(state.hotkeys))
                if uid in associations
            },
        )
