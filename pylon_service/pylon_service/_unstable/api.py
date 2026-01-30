from litestar import Controller
from litestar.di import Provide
from pylon_commons._unstable import SubnetCommitments
from pylon_commons._unstable.endpoints import Endpoint
from pylon_commons.types import NetUid

from pylon_service.api import handler
from pylon_service.bittensor.client import AbstractBittensorClient
from pylon_service.dependencies import bt_client_identity_dep, bt_client_open_access_dep, identity_dep


class OpenAccessController(Controller):
    path = "/subnet/{netuid:int}/"
    dependencies = {
        "bt_client": Provide(bt_client_open_access_dep),
    }

    @handler(Endpoint.LATEST_COMMITMENTS)
    async def get_commitments_endpoint(self, bt_client: AbstractBittensorClient, netuid: NetUid) -> SubnetCommitments:
        block = await bt_client.get_latest_block()
        return await bt_client.get_commitments(netuid, block)


class IdentityController(OpenAccessController):
    path = "/identity/{identity_name:str}/subnet/{netuid:int}"
    dependencies = {
        "identity": Provide(identity_dep),
        "bt_client": Provide(bt_client_identity_dep),
    }
