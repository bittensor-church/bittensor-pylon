from pylon_commons.types import NetUid
from pylon_commons.v1.endpoints import Endpoint
from pylon_commons.v1.responses import GetCommitmentsResponse

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
        Get all commitments for the subnet.
        """
        block = await bt_client.get_latest_block()
        result = await bt_client.get_commitments(netuid, block)
        return GetCommitmentsResponse(
            block=result.block,
            commitments={hotkey: c.commitment for hotkey, c in result.commitments.items()},
        )


class IdentityController(OpenAccessController, NewIdentityController):
    pass


__all__ = [
    "OpenAccessController",
    "IdentityController",
    "identity_login",
    "get_extrinsic_endpoint",
    "get_latest_block_info_endpoint",
]
