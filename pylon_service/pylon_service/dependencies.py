from collections.abc import AsyncGenerator

from litestar import Request
from litestar.datastructures import State
from litestar.di import Provide
from litestar.exceptions import NotFoundException
from pylon_commons.types import IdentityName, NetUid

from pylon_service.api._unstable.services import (
    BlockService,
    CertificateService,
    CommitmentService,
    DrandService,
    NeuronService,
    WeightService,
)
from pylon_service.api.v1.services import (
    CommitmentService as V1CommitmentService,
)
from pylon_service.api.v1.services import (
    WeightService as V1WeightService,
)
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


async def unstable_block_service_dep(
    bt_contact_router: BittensorContactRouter,
) -> BlockService:
    return BlockService(bt_contact_router)


async def unstable_neuron_service_dep(
    bt_contact_router: BittensorContactRouter,
) -> NeuronService:
    return NeuronService(bt_contact_router)


async def unstable_certificate_service_dep(
    bt_contact_router: BittensorContactRouter,
) -> CertificateService:
    return CertificateService(bt_contact_router)


async def unstable_commitment_service_dep(
    bt_contact_router: BittensorContactRouter,
) -> CommitmentService:
    return CommitmentService(bt_contact_router)


async def unstable_weight_service_dep(
    identity: Identity,
    bt_contact_router: BittensorContactRouter,
) -> WeightService:
    return WeightService(identity, bt_contact_router)


async def unstable_drand_service_dep(
    bt_contact_router: BittensorContactRouter,
) -> DrandService:
    return DrandService(bt_contact_router)


async def v1_commitment_service_dep(
    bt_contact_router: BittensorContactRouter,
    unstable_commitment_service: CommitmentService,
) -> V1CommitmentService:
    return V1CommitmentService(bt_contact_router, unstable_commitment_service)


async def v1_weight_service_dep(
    identity: Identity,
    bt_contact_router: BittensorContactRouter,
) -> V1WeightService:
    return V1WeightService(identity, bt_contact_router)


SERVICE_PROVIDERS = {
    "unstable_block_service": Provide(unstable_block_service_dep),
    "unstable_neuron_service": Provide(unstable_neuron_service_dep),
    "unstable_certificate_service": Provide(unstable_certificate_service_dep),
    "unstable_commitment_service": Provide(unstable_commitment_service_dep),
    "unstable_weight_service": Provide(unstable_weight_service_dep),
    "unstable_drand_service": Provide(unstable_drand_service_dep),
    "v1_commitment_service": Provide(v1_commitment_service_dep),
    "v1_weight_service": Provide(v1_weight_service_dep),
}

PUBLIC_PROVIDERS = {
    "bt_contact_router": Provide(bt_contact_router_open_access_dep),
    **SERVICE_PROVIDERS,
}

OPEN_ACCESS_PROVIDERS = {
    "bt_contact_router": Provide(bt_contact_router_open_access_dep),
    "recent_object_provider": Provide(recent_object_provider_open_access_dep),
    **SERVICE_PROVIDERS,
}

IDENTITY_PROVIDERS = {
    "identity": Provide(identity_dep),
    "bt_contact_router": Provide(bt_contact_router_identity_dep),
    "recent_object_provider": Provide(recent_object_provider_identity_dep),
    **SERVICE_PROVIDERS,
}
