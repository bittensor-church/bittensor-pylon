from litestar.exceptions import NotFoundException
from pylon_commons.models import CommitmentKind
from pylon_commons.types import Hotkey, NetUid
from pylon_commons.v1.endpoints import Endpoint
from pylon_commons.v1.responses import GetCommitmentResponse, GetCommitmentsResponse

from pylon_service.api._unstable.api import (
    IdentityController as NewIdentityController,
)
from pylon_service.api._unstable.api import (
    OpenAccessController as NewOpenAccessController,
)
from pylon_service.api._unstable.api import (
    get_extrinsic_endpoint,
    get_latest_block_info_endpoint,
    identity_login,
)
from pylon_service.api.utils import handler
from pylon_service.bittensor.client import AbstractBittensorClient


class OpenAccessController(NewOpenAccessController):
    @handler(Endpoint.LATEST_COMMITMENTS)
    async def get_commitments_endpoint(
        self, bt_client: AbstractBittensorClient, netuid: NetUid
    ) -> GetCommitmentsResponse:
        """
        Get all hex data commitments for the subnet. Ignores timelock encrypted commitments.
        """
        block = await bt_client.get_latest_block()
        result = await bt_client.get_commitments(netuid, block)
        return GetCommitmentsResponse(
            block=result.block,
            commitments={
                hotkey: c.commitment for hotkey, c in result.commitments.items() if c.kind == CommitmentKind.HEX_DATA
            },
        )

    @handler(Endpoint.LATEST_COMMITMENTS_HOTKEY)
    async def get_commitment_endpoint(
        self, hotkey: Hotkey, bt_client: AbstractBittensorClient, netuid: NetUid
    ) -> GetCommitmentResponse:
        """
        Get a hex data commitment for a hotkey.

        Raises:
            NotFoundException: If a commitment could not be found in the blockchain or there is only timelock encrypted commitment.
        """
        block = await bt_client.get_latest_block()
        commitment = await bt_client.get_commitment(netuid, block, hotkey=hotkey)
        if commitment is None or commitment.kind != CommitmentKind.HEX_DATA:
            raise NotFoundException(detail="Commitment not found.")
        return GetCommitmentResponse(
            block=block,
            commitment_block_number=commitment.commitment_block_number,
            hotkey=commitment.hotkey,
            commitment=commitment.commitment,
        )


class IdentityController(OpenAccessController, NewIdentityController):
    @handler(Endpoint.LATEST_COMMITMENTS_SELF)
    async def get_own_commitment_endpoint(
        self, bt_client: AbstractBittensorClient, netuid: NetUid
    ) -> GetCommitmentResponse:
        """
        Get a hex data commitment for the identity's wallet.

        Raises:
            NotFoundException: If a commitment could not be found in the blockchain or there is only timelock encrypted commitment.
        """
        block = await bt_client.get_latest_block()
        commitment = await bt_client.get_commitment(netuid, block)
        if commitment is None or commitment.kind != CommitmentKind.HEX_DATA:
            raise NotFoundException(detail="Commitment not found.")
        return GetCommitmentResponse(
            block=block,
            commitment_block_number=commitment.commitment_block_number,
            hotkey=commitment.hotkey,
            commitment=commitment.commitment,
        )


__all__ = [
    "OpenAccessController",
    "IdentityController",
    "identity_login",
    "get_extrinsic_endpoint",
    "get_latest_block_info_endpoint",
]
