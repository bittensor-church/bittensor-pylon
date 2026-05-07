from pylon_commons.models import (
    BlockInfoBag,
    CommitmentVariant,
    Extrinsic,
    RevealedCommitment,
    SubnetCommitments,
    SubnetNeurons,
    SubnetRevealedCommitments,
    SubnetValidators,
)
from pylon_commons.types import (
    BlockNumber,
    CommitmentDataBytes,
    ExtrinsicIndex,
    Hotkey,
    MechanismId,
    NetUid,
    RevealedCommitmentData,
    Weight,
)

from pylon_service.api._unstable.tasks import ApplyWeights, SetCommitment, SetRevealedCommitment
from pylon_service.bittensor.contact import BittensorPort
from pylon_service.bittensor.models import (
    Block,
    CertificateAlgorithm,
    NeuronCertificate,
    NeuronCertificateKeypair,
)
from pylon_service.bittensor.recent import RecentObjectMissing, RecentObjectProvider, RecentObjectStale
from pylon_service.exceptions import BadGatewayException
from pylon_service.service_errors import (
    BlockNotFoundError,
    CertificateGenerationFailedError,
    CertificateNotFoundError,
    CommitmentNotFoundError,
    ExtrinsicNotFoundError,
    RecentObjectMissingError,
    RecentObjectStaleError,
)


class BlockService:
    @staticmethod
    async def get_latest_block_info(contact_router: BittensorPort) -> BlockInfoBag:
        block = await contact_router.get_latest_block()
        timestamp = await contact_router.get_block_timestamp(block)
        return BlockInfoBag(number=block.number, hash=block.hash, timestamp=timestamp)

    @staticmethod
    async def get_extrinsic(
        contact_router: BittensorPort, block_number: BlockNumber, extrinsic_index: ExtrinsicIndex
    ) -> Extrinsic:
        block = await contact_router.get_block(block_number)
        if block is None:
            raise BlockNotFoundError(f"Block {block_number} not found.")

        extrinsic = await contact_router.get_extrinsic(block, extrinsic_index)
        if extrinsic is None:
            raise ExtrinsicNotFoundError(f"Extrinsic {block_number}-{extrinsic_index} not found.")

        return extrinsic


class NeuronService:
    @staticmethod
    async def get_neurons(contact_router: BittensorPort, netuid: NetUid, block_number: BlockNumber) -> SubnetNeurons:
        block = await contact_router.get_block(block_number)
        if block is None:
            raise BlockNotFoundError(f"Block {block_number} not found.")

        return await contact_router.get_neurons(netuid, block)

    @staticmethod
    async def get_latest_neurons(contact_router: BittensorPort, netuid: NetUid) -> SubnetNeurons:
        block = await contact_router.get_latest_block()
        return await contact_router.get_neurons(netuid, block)

    @staticmethod
    async def get_recent_neurons(recent_object_provider: RecentObjectProvider) -> SubnetNeurons:
        try:
            return await recent_object_provider.get(SubnetNeurons)
        except RecentObjectMissing as exc:
            raise RecentObjectMissingError(
                "Recent neurons data is not available. Cache update may not have finished "
                "yet or subnet may not be configured for caching recent objects."
            ) from exc
        except RecentObjectStale as exc:
            raise RecentObjectStaleError("Recent neurons data is stale. Cache update may be failing.") from exc

    @staticmethod
    async def get_validators(
        contact_router: BittensorPort, netuid: NetUid, block_number: BlockNumber
    ) -> SubnetValidators:
        block = await contact_router.get_block(block_number)
        if block is None:
            raise BlockNotFoundError(f"Block {block_number} not found.")

        subnet_neurons = await contact_router.get_neurons(netuid, block)
        validators = [neuron for neuron in subnet_neurons.neurons.values() if neuron.validator_permit]
        validators.sort(key=lambda neuron: neuron.stakes.total, reverse=True)
        return SubnetValidators(block=block, validators=validators)

    @staticmethod
    async def get_latest_validators(contact_router: BittensorPort, netuid: NetUid) -> SubnetValidators:
        block = await contact_router.get_latest_block()
        subnet_neurons = await contact_router.get_neurons(netuid, block)
        validators = [neuron for neuron in subnet_neurons.neurons.values() if neuron.validator_permit]
        validators.sort(key=lambda neuron: neuron.stakes.total, reverse=True)
        return SubnetValidators(block=block, validators=validators)


class CertificateService:
    @staticmethod
    async def get_certificates(contact_router: BittensorPort, netuid: NetUid) -> dict[Hotkey, NeuronCertificate]:
        block = await contact_router.get_latest_block()
        return await contact_router.get_certificates(netuid, block)

    @staticmethod
    async def get_certificate(contact_router: BittensorPort, netuid: NetUid, hotkey: Hotkey) -> NeuronCertificate:
        block = await contact_router.get_latest_block()
        certificate = await contact_router.get_certificate(netuid, block, hotkey=hotkey)
        if certificate is None:
            raise CertificateNotFoundError("Certificate not found or error fetching.")
        return certificate

    @staticmethod
    async def get_own_certificate(contact_router: BittensorPort, netuid: NetUid) -> NeuronCertificate:
        block = await contact_router.get_latest_block()
        certificate = await contact_router.get_certificate(netuid, block)
        if certificate is None:
            raise CertificateNotFoundError("Certificate not found or error fetching.")
        return certificate

    @staticmethod
    async def generate_certificate_keypair(
        contact_router: BittensorPort, netuid: NetUid, algorithm: CertificateAlgorithm
    ) -> NeuronCertificateKeypair:
        certificate_keypair = await contact_router.generate_certificate_keypair(netuid, algorithm)
        if certificate_keypair is None:
            raise CertificateGenerationFailedError("Could not generate certificate pair.")
        return certificate_keypair


class CommitmentService:
    @staticmethod
    async def set_commitment(contact_router: BittensorPort, netuid: NetUid, data: CommitmentDataBytes) -> None:
        try:
            await SetCommitment(contact_router, netuid, data)()
        except Exception as exc:
            raise BadGatewayException(detail=str(exc)) from exc

    @staticmethod
    async def get_commitments(contact_router: BittensorPort, netuid: NetUid) -> SubnetCommitments:
        block = await contact_router.get_latest_block()

        raw_commitments = await contact_router.get_commitments(netuid, block)
        state = await contact_router.get_subnet_state(netuid, block)
        if state is None:
            raise RuntimeError(f"Subnet state is unavailable for netuid {netuid} at block {block.number}.")
        registered_hotkeys = set(state.hotkeys)
        filtered = {
            hotkey: commitment
            for hotkey, commitment in raw_commitments.commitments.items()
            if hotkey in registered_hotkeys
        }
        return SubnetCommitments(block=raw_commitments.block, commitments=filtered)

    @staticmethod
    async def get_commitment(
        contact_router: BittensorPort, netuid: NetUid, hotkey: Hotkey
    ) -> tuple[Block, CommitmentVariant]:
        block = await contact_router.get_latest_block()
        commitment = await contact_router.get_commitment(netuid, block, hotkey=hotkey)
        if commitment is None:
            raise CommitmentNotFoundError("Commitment not found.")
        return block, commitment

    @staticmethod
    async def get_own_commitment(contact_router: BittensorPort, netuid: NetUid) -> tuple[Block, CommitmentVariant]:
        block = await contact_router.get_latest_block()
        commitment = await contact_router.get_commitment(netuid, block)
        if commitment is None:
            raise CommitmentNotFoundError("Commitment not found.")
        return block, commitment

    @staticmethod
    async def set_revealed_commitment(
        contact_router: BittensorPort, netuid: NetUid, commitment: RevealedCommitmentData, block_until_reveal: int
    ) -> int:
        # TODO returning reveal_round prevents changing this to really async (not waiting for the task to finish)
        try:
            return await SetRevealedCommitment(contact_router, netuid, commitment, block_until_reveal)()
        except Exception as exc:
            raise BadGatewayException(detail=str(exc)) from exc

    @staticmethod
    async def get_all_revealed_commitments(contact_router: BittensorPort, netuid: NetUid) -> SubnetRevealedCommitments:
        block = await contact_router.get_latest_block()
        return await contact_router.get_all_revealed_commitments(netuid, block)

    @staticmethod
    async def get_revealed_commitments(
        contact_router: BittensorPort, netuid: NetUid, hotkey: Hotkey | None = None
    ) -> tuple[Block, list[RevealedCommitment]]:
        block = await contact_router.get_latest_block()
        commitments = await contact_router.get_revealed_commitments(netuid, block, hotkey=hotkey)
        if commitments is None:
            raise CommitmentNotFoundError("Revealed commitments not found.")
        return block, commitments

    @staticmethod
    async def get_own_revealed_commitments(
        contact_router: BittensorPort, netuid: NetUid
    ) -> tuple[Block, list[RevealedCommitment]]:
        block = await contact_router.get_latest_block()
        commitments = await contact_router.get_revealed_commitments(netuid, block)
        if commitments is None:
            raise CommitmentNotFoundError("Revealed commitments not found.")
        return block, commitments


class WeightService:
    @staticmethod
    async def set_weights(
        contact_router: BittensorPort, netuid: NetUid, mechanism_id: MechanismId, weights: dict[Hotkey, Weight]
    ):
        ApplyWeights(contact_router, weights, netuid, mechanism_id).schedule()
