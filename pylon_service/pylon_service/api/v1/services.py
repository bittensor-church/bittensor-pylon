from pylon_commons.models import CommitmentVariant, CommitmentKind
from pylon_commons.types import Hotkey, NetUid
from pylon_commons.v1.responses import GetCommitmentResponse, GetCommitmentsResponse

from pylon_service.api._unstable.services import BlockService, CertificateService, NeuronService  # noqa: F401
from pylon_service.bittensor.contact import BittensorPort
from pylon_service.bittensor.models import Block
from pylon_service.services.commitments import CommitmentService as DomainCommitmentService
from pylon_service.services.errors import CommitmentNotFoundError


class CommitmentService:
    def __init__(self) -> None:
        self._domain = DomainCommitmentService()

    async def get_commitments(self, contact_router: BittensorPort, netuid: NetUid) -> GetCommitmentsResponse:
        block = await contact_router.get_latest_block()
        commitments = await self._domain.get_commitments(contact_router, netuid, block)
        return GetCommitmentsResponse(
            block=commitments.block,
            commitments={hotkey: c.commitment for hotkey, c in c.commitments.items() if c.kind == CommitmentKind.HEX_DATA},
        )

    async def get_commitment(
        self, contact_router: BittensorPort, netuid: NetUid, hotkey: Hotkey
    ) -> GetCommitmentResponse:
        block, commitment = await self._domain.get_commitment(contact_router, netuid, hotkey)
        if commitment.kind != CommitmentKind.HEX_DATA:
            raise CommitmentNotFoundError()
        return self._wrap_commitment(block, commitment)

    async def get_own_commitment(self, contact_router: BittensorPort, netuid: NetUid) -> GetCommitmentResponse:
        block, commitment = await self._domain.get_own_commitment(contact_router, netuid)
        if commitment.kind != CommitmentKind.HEX_DATA:
            raise CommitmentNotFoundError()
        return self._wrap_commitment(block, commitment)

    @staticmethod
    def _wrap_commitment(block: Block, commitment: CommitmentVariant) -> GetCommitmentResponse:
        return GetCommitmentResponse(block=block, **commitment.model_dump())
