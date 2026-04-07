from pylon_commons.v1.responses import GetCommitmentsResponse
from pylon_commons.types import NetUid

from pylon_service.bittensor.contact import BittensorPort
from pylon_service.api._unstable.services import (  # noqa: F401
    BlockService,
    CertificateService,
    CommitmentService as UnstableCommitmentService,
    NeuronService,
)


class CommitmentService(UnstableCommitmentService):
    async def get_commitments(self, router: BittensorPort, netuid: NetUid) -> GetCommitmentsResponse:
        commitments = await self.get_latest_commitments(router, netuid)
        return GetCommitmentsResponse(
            block=commitments.block,
            commitments={hotkey: commitment.commitment for hotkey, commitment in commitments.commitments.items()},
        )
