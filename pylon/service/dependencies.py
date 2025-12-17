from collections.abc import AsyncGenerator
from typing import TypeVar

from litestar.datastructures import State
from litestar.exceptions import NotFoundException

from pylon._internal.common.types import IdentityName
from pylon.service.bittensor.cache.recent import RecentDataProvider
from pylon.service.bittensor.client import AbstractBittensorClient
from pylon.service.bittensor.pool import BittensorClientPool
from pylon.service.identities import Identity, identities
from pylon.service.settings import settings

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


async def recent_data_provider_dep(state: State) -> RecentDataProvider:
    return RecentDataProvider(
        soft_limit=settings.recent_objects_soft_limit,
        hard_limit=settings.recent_objects_hard_limit,
        store=state.store,
    )


# 'identity' dep is needed to make 'identity_name' required in the URL. 'recent_data_provider_dep'
# doesn't have a use for identity for now. But it might be useful in the future.
# noinspection PyUnusedLocal
async def recent_data_provider_identity_dep(state: State, identity: Identity) -> RecentDataProvider:
    return await recent_data_provider_dep(state)
