from pylon_commons.models import CommitmentKind
from pylon_commons.types import CommitmentDataHex, Hotkey, MechanismId, NetUid, Weight
from pylon_commons.v1.models import Commitment as V1Commitment

from pylon_service.api._unstable.services import CommitmentService as UnstableCommitmentService
from pylon_service.api._unstable.tasks import ApplyWeights as UnstableApplyWeights
from pylon_service.api.services import BaseService, CommitmentNotFoundError
from pylon_service.bittensor.contact import BittensorPort
from pylon_service.bittensor.models import Block
from pylon_service.identities import Identity


class CommitmentService(BaseService):
    def __init__(self, contact_router: BittensorPort, unstable_commitment_service: UnstableCommitmentService) -> None:
        super().__init__(contact_router)
        self.unstable_commitment_service = unstable_commitment_service

    async def get_commitments(self, netuid: NetUid) -> tuple[Block, dict[Hotkey, CommitmentDataHex]]:
        subnet_commitments = await self.unstable_commitment_service.get_commitments(netuid)
        return (
            subnet_commitments.block,
            {
                hotkey: commitment.commitment
                for hotkey, commitment in subnet_commitments.commitments.items()
                if commitment.kind == CommitmentKind.HEX_DATA
            },
        )

    async def get_commitment(self, netuid: NetUid, hotkey: Hotkey) -> tuple[Block, V1Commitment]:
        block, commitment = await self.unstable_commitment_service.get_commitment(netuid, hotkey)
        if commitment.kind != CommitmentKind.HEX_DATA:
            raise CommitmentNotFoundError()
        return block, V1Commitment.model_validate(commitment, from_attributes=True)

    async def get_own_commitment(self, netuid: NetUid) -> tuple[Block, V1Commitment]:
        block, commitment = await self.unstable_commitment_service.get_own_commitment(netuid)
        if commitment.kind != CommitmentKind.HEX_DATA:
            raise CommitmentNotFoundError()
        return block, V1Commitment.model_validate(commitment, from_attributes=True)


class WeightService(BaseService):
    def __init__(self, identity: Identity, contact_router: BittensorPort) -> None:
        super().__init__(contact_router)
        self.identity = identity

    async def set_weights(self, netuid: NetUid, weights: dict[Hotkey, Weight]):
        await UnstableApplyWeights(self.identity, self.contact_router, weights, netuid, MechanismId(0)).schedule()
