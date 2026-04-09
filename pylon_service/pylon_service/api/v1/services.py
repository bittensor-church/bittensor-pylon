from pylon_commons.types import Hotkey, NetUid
from pylon_commons.v1.responses import GetCommitmentResponse, GetCommitmentsResponse

from pylon_service.api._unstable.services import BlockService, CertificateService, NeuronService  # noqa: F401
from pylon_service.bittensor.contact import BittensorPort
from pylon_service.bittensor.models import Block, Commitment
from pylon_service.services.commitments import CommitmentService as DomainCommitmentService


class CommitmentService:
    def __init__(self) -> None:
        self._domain = DomainCommitmentService()

    async def get_commitments(self, contact_router: BittensorPort, netuid: NetUid) -> GetCommitmentsResponse:
        block = await contact_router.get_latest_block()
        commitments = await self._domain.get_commitments(contact_router, netuid, block)
        return GetCommitmentsResponse(
            block=commitments.block,
            commitments={hotkey: commitment.commitment for hotkey, commitment in commitments.commitments.items()},
        )

    async def get_commitment(
        self, contact_router: BittensorPort, netuid: NetUid, hotkey: Hotkey
    ) -> GetCommitmentResponse:
        block, commitment = await self._domain.get_commitment(contact_router, netuid, hotkey)
        return self._wrap_commitment(block, commitment)

    async def get_own_commitment(self, contact_router: BittensorPort, netuid: NetUid) -> GetCommitmentResponse:
        block, commitment = await self._domain.get_own_commitment(contact_router, netuid)
        return self._wrap_commitment(block, commitment)

    @staticmethod
    def _wrap_commitment(block: Block, commitment: Commitment) -> GetCommitmentResponse:
        return GetCommitmentResponse(block=block, **commitment.model_dump())
