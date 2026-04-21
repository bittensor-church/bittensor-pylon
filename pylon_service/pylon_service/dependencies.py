from collections.abc import AsyncGenerator

from litestar import Request
from litestar.datastructures import State
from litestar.exceptions import NotFoundException
from pylon_commons.types import IdentityName, NetUid

from pylon_service.bittensor.contact_router import BittensorContactRouter
from pylon_service.bittensor.pool import BittensorContactPool
from pylon_service.bittensor.recent import (
    AbstractContext,
    IdentitySubnetContext,
    RecentObjectProvider,
    SubnetContext,
)
from pylon_service.identities import Identity, identities
from pylon_service.settings import recent_objects_settings, settings
from pylon_service.stores import StoreName


async def bt_contact_pool_dep(state: State) -> BittensorContactPool:
    """
    Pool of bittensor contact routers. Every contact router used in the service should be taken from the pool to
    maintain and reuse connections.
    """
    return state.bittensor_contact_pool


async def identity_dep(identity_name: IdentityName) -> Identity:
    if identity_ := identities.get(identity_name):
        return identity_
    raise NotFoundException(f"Identity '{identity_name}' not found")


async def bt_contact_router_identity_dep(
    bt_contact_pool: BittensorContactPool[BittensorContactRouter], identity: Identity
) -> AsyncGenerator[BittensorContactRouter]:
    async with bt_contact_pool.acquire(wallet=identity.wallet) as contact_router:
        yield contact_router


async def bt_contact_router_open_access_dep(
    bt_contact_pool: BittensorContactPool[BittensorContactRouter],
) -> AsyncGenerator[BittensorContactRouter]:
    async with bt_contact_pool.acquire(wallet=None) as contact_router:
        yield contact_router


def _create_recent_object_provider(request: Request, context: AbstractContext) -> RecentObjectProvider:
    return RecentObjectProvider(
        soft_limit=recent_objects_settings.soft_limit_blocks,
        hard_limit=recent_objects_settings.hard_limit_blocks,
        block_duration_seconds=settings.block_duration_seconds,
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
