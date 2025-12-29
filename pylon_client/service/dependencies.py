from collections.abc import AsyncGenerator
from typing import TypeVar

from litestar import Request
from litestar.datastructures import State
from litestar.exceptions import NotFoundException

from pylon_client._internal.common.types import IdentityName, NetUid
from pylon_client.service.bittensor.client import AbstractBittensorClient
from pylon_client.service.bittensor.pool import BittensorClientPool
from pylon_client.service.bittensor.recent import (
    AbstractContext,
    IdentitySubnetContext,
    RecentObjectProvider,
    SubnetContext,
)
from pylon_client.service.identities import Identity, identities
from pylon_client.service.settings import recent_objects_settings
from pylon_client.service.stores import StoreName

BtClient = TypeVar("BtClient", bound=AbstractBittensorClient)


async def bt_client_pool_dep(state: State) -> BittensorClientPool:
    """
    Pool of bittensor clients. Every client used in the service should be taken from the pool to maintain and reuse
    connections.
    """
    return state.bittensor_client_pool


async def identity_dep(identity_name: IdentityName) -> Identity:
    # TODO: When authentication is added, identity will be fetched from the session. A Guard will guarantee that the
    #   data from identity in the session matches the data in an url.
    if identity_ := identities.get(identity_name):
        return identity_
    raise NotFoundException(f"Identity '{identity_name}' not found")


async def bt_client_identity_dep(
    bt_client_pool: BittensorClientPool[BtClient], identity: Identity
) -> AsyncGenerator[BtClient]:
    async with bt_client_pool.acquire(wallet=identity.wallet) as client:
        yield client


async def bt_client_open_access_dep(bt_client_pool: BittensorClientPool[BtClient]) -> AsyncGenerator[BtClient]:
    async with bt_client_pool.acquire(wallet=None) as client:
        yield client


def _create_recent_object_provider(request: Request, context: AbstractContext) -> RecentObjectProvider:
    return RecentObjectProvider(
        soft_limit=recent_objects_settings.soft_limit_blocks,
        hard_limit=recent_objects_settings.hard_limit_blocks,
        store=request.app.stores.get(StoreName.RECENT_OBJECTS),
        context=context,
    )


async def recent_object_provider_open_access_dep(netuid: NetUid, request: Request) -> RecentObjectProvider:
    return _create_recent_object_provider(request, SubnetContext(netuid))


async def recent_object_provider_identity_dep(
    netuid: NetUid, identity: Identity, request: Request
) -> RecentObjectProvider:
    context = IdentitySubnetContext(netuid, identity.wallet)
    return _create_recent_object_provider(request, context)
