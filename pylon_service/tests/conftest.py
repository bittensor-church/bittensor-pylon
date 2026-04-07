"""
Shared fixtures for all service tests (unit and pact).
"""

from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
import pytest_asyncio
from bittensor_wallet import Wallet
from polyfactory.pytest_plugin import register_fixture
from pylon_commons.types import ArchiveBlocksCutoff
from pylon_commons.types import IdentityName
from syrupy.extensions.json import JSONSnapshotExtension
from syrupy.matchers import path_type

from pylon_service import lifespans, main
from pylon_service import dependencies, identities as identities_module
from pylon_service.bittensor.contact import ContactFactory
from pylon_service.bittensor.pool import BittensorClientPool
from pylon_service.bittensor.router import BittensorRouter
from pylon_service.main import create_app
from pylon_service.stores import StoreName
from tests.factories import BlockFactory, NeuronFactory
from tests.mock_bittensor_client import MockBittensorClient
from tests.mock_store import MockStore
from tests.world import (
    SharedWorld,
    build_test_identities,
    default_commitments,
    default_latest_block,
    default_neurons,
    default_subnet_states,
)

register_fixture(BlockFactory)
register_fixture(NeuronFactory)

TEST_IDENTITIES = build_test_identities()
identities_module.identities.clear()
identities_module.identities.update(TEST_IDENTITIES)
dependencies.identities = identities_module.identities


@pytest.fixture
def snapshot_json(snapshot):
    return snapshot.use_extension(JSONSnapshotExtension)


@pytest.fixture
def response_matchers():
    def factory(*, timestamp_paths: tuple[str, ...] = (), regex_paths: dict[str, tuple[type, ...]] | None = None):
        mapping: dict[str, tuple[type, ...]] = {path: (int,) for path in timestamp_paths}
        if regex_paths:
            mapping.update(regex_paths)
        return path_type(mapping, regex=True)

    return factory


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def mock_bt_client_pool():
    """
    Create a mock Bittensor client pool.
    """
    async with BittensorClientPool(
        router_cls=BittensorRouter,
        contact_factory=ContactFactory(contact_cls=MockBittensorClient),
        uri="mock://main",
        archive_uri="mock://archive",
        archive_blocks_cutoff=ArchiveBlocksCutoff(10_000_000),
    ) as pool:
        yield pool


@pytest.fixture(scope="session")
def mock_stores():
    return {
        StoreName.RECENT_OBJECTS: MockStore(),
    }


@pytest.fixture(autouse=True)
def reset_mock_stores(mock_stores):
    yield
    for store in mock_stores.values():
        store.reset()


@pytest.fixture(scope="session")
def test_app(mock_bt_client_pool, mock_stores):
    """
    Create a test Litestar app with the mock client pool.
    """

    # Mock the bittensor_client lifespan to just set our mock client
    @asynccontextmanager
    async def mock_lifespan(app):
        app.state.bittensor_client_pool = mock_bt_client_pool
        yield

    # Mock the scheduler lifespan to prevent background task execution during tests
    @asynccontextmanager
    async def mock_scheduler_lifespan(app):
        yield

    with (
        patch.object(lifespans, "bittensor_client_pool", mock_lifespan),
        patch.object(lifespans, "scheduler_lifespan", mock_scheduler_lifespan),
        # Litestar appends its own stuff to the dict we give it - so let's give it a copy, otherwise we end up
        # resetting the cache store which we don't care about here. (caching is already disabled directly for tests)
        patch.object(main, "stores", {**mock_stores}),
    ):
        app = create_app()

        # Disable cache by marking all responses uncacheable
        app.response_cache_config.cache_response_filter = lambda _, __: False

        # Enable detailed error responses
        app.debug = True

        yield app


@pytest.fixture
def wallet():
    return Wallet(path="tests/wallets", name="pylon", hotkey="pylon")


@pytest_asyncio.fixture
async def open_access_mock_bt_client(mock_bt_client_pool):
    async with mock_bt_client_pool.acquire(wallet=None) as router:
        yield router._main_contact
        router._main_contact.reset()
        router._archive_contact.reset()


@pytest_asyncio.fixture
async def sn1_mock_bt_client(mock_bt_client_pool):
    async with mock_bt_client_pool.acquire(wallet=TEST_IDENTITIES[IdentityName("sn1")].wallet) as router:
        yield router._main_contact
        router._main_contact.reset()
        router._archive_contact.reset()


@pytest_asyncio.fixture
async def sn2_mock_bt_client(mock_bt_client_pool):
    async with mock_bt_client_pool.acquire(wallet=TEST_IDENTITIES[IdentityName("sn2")].wallet) as router:
        yield router._main_contact
        router._main_contact.reset()
        router._archive_contact.reset()


@pytest_asyncio.fixture(scope="session")
async def shared_world(mock_bt_client_pool) -> SharedWorld:
    async with mock_bt_client_pool.acquire(wallet=None) as open_access_router:
        async with mock_bt_client_pool.acquire(wallet=TEST_IDENTITIES[IdentityName("sn1")].wallet) as sn1_router:
            async with mock_bt_client_pool.acquire(wallet=TEST_IDENTITIES[IdentityName("sn2")].wallet) as sn2_router:
                yield SharedWorld(
                    open_access_main=open_access_router._main_contact,
                    open_access_archive=open_access_router._archive_contact,
                    sn1_main=sn1_router._main_contact,
                    sn1_archive=sn1_router._archive_contact,
                    sn2_main=sn2_router._main_contact,
                    sn2_archive=sn2_router._archive_contact,
                    identities=TEST_IDENTITIES,
                    default_latest_block=default_latest_block(),
                    default_neurons=default_neurons(),
                    default_subnet_states=default_subnet_states(),
                    default_commitments=default_commitments(),
                )


@pytest.fixture(autouse=True)
def reset_shared_world(shared_world: SharedWorld):
    shared_world.reset()
    shared_world.seed_defaults()
    yield
