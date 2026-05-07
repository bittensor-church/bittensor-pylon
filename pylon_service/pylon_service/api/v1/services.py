from pylon_commons.models import CommitmentKind
from pylon_commons.types import CommitmentDataHex, Hotkey, MechanismId, NetUid, Weight
from pylon_commons.v1.models import Commitment as V1Commitment

from pylon_service.api._unstable.services import CommitmentService as UnstableCommitmentService
from pylon_service.api._unstable.tasks import ApplyWeights
from pylon_service.bittensor.contact import BittensorPort
from pylon_service.bittensor.models import Block
from pylon_service.service_errors import CommitmentNotFoundError


class CommitmentService:
    @staticmethod
    async def get_commitments(
        contact_router: BittensorPort, netuid: NetUid
    ) -> tuple[Block, dict[Hotkey, CommitmentDataHex]]:
        subnet_commitments = await UnstableCommitmentService.get_commitments(contact_router, netuid)
        return (
            subnet_commitments.block,
            {
                hotkey: commitment.commitment
                for hotkey, commitment in subnet_commitments.commitments.items()
                if commitment.kind == CommitmentKind.HEX_DATA
            },
        )

    @staticmethod
    async def get_commitment(
        contact_router: BittensorPort, netuid: NetUid, hotkey: Hotkey
    ) -> tuple[Block, V1Commitment]:
        block, commitment = await UnstableCommitmentService.get_commitment(contact_router, netuid, hotkey)
        if commitment.kind != CommitmentKind.HEX_DATA:
            raise CommitmentNotFoundError()
        return block, V1Commitment.model_validate(commitment, from_attributes=True)

    @staticmethod
    async def get_own_commitment(contact_router: BittensorPort, netuid: NetUid) -> tuple[Block, V1Commitment]:
        block, commitment = await UnstableCommitmentService.get_own_commitment(contact_router, netuid)
        if commitment.kind != CommitmentKind.HEX_DATA:
            raise CommitmentNotFoundError()
        return block, V1Commitment.model_validate(commitment, from_attributes=True)


class WeightService:
    @staticmethod
    async def set_weights(contact_router: BittensorPort, netuid: NetUid, weights: dict[Hotkey, Weight]):
        ApplyWeights(contact_router, weights, netuid, MechanismId(0)).schedule()
