"""
Shared fixtures for all service tests (unit and pact).
"""

from collections.abc import AsyncGenerator
from contextlib import AsyncExitStack, asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio
from bittensor_wallet import Wallet
from polyfactory.pytest_plugin import register_fixture
from pylon_commons.types import ArchiveBlocksCutoff, IdentityName
from sqlalchemy import delete
from syrupy.extensions.json import JSONSnapshotExtension

from pylon_service import identities as identities_module
from pylon_service import lifecycle, main
from pylon_service.bittensor.contact import ContactFactory
from pylon_service.bittensor.contact_router import BittensorContactRouter
from pylon_service.bittensor.mock_contact import MockBittensorContact
from pylon_service.bittensor.pool import BittensorContactPool
from pylon_service.db.database import session_factory
from pylon_service.db.models import WeightTask
from pylon_service.main import create_app
from pylon_service.settings import database_settings, settings
from pylon_service.stores import StoreName
from tests.factories import BlockFactory, NeuronFactory
from tests.fixture_contract import EXPECTED_IDENTITIES, assert_test_fixture_contract
from tests.mock_store import MockStore
from tests.world import (
    IdentityContacts,
    SharedWorld,
    default_commitments,
    default_evm_assocations,
    default_latest_block,
    default_neurons,
    default_revealed_commitments,
    default_subnet_states,
)

register_fixture(BlockFactory)
register_fixture(NeuronFactory)

TEST_IDENTITIES = identities_module.identities


def pytest_configure() -> None:
    try:
        assert_test_fixture_contract(settings=settings, identities=TEST_IDENTITIES)
    except RuntimeError as exc:
        raise pytest.UsageError(str(exc)) from exc


@pytest.fixture
def snapshot_json(snapshot):
    return snapshot.use_extension(JSONSnapshotExtension)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def mock_bt_contact_pool():
    """
    Create a mock Bittensor contact pool.
    """
    async with BittensorContactPool(
        contact_router_cls=BittensorContactRouter,
        contact_factory=ContactFactory(contact_cls=MockBittensorContact),
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
def setup_test_database():
    """
    Create a test DB directory if not exists. Clean up any existing database files.

    The database is intentionally left on disk after the test run, so it can be inspected for debugging reasons.

    Raises:
        pytest.UsageError: If ``PYLON_DATABASE_PATH`` is not set for tests.
    """
    if database_settings.path is None:
        raise pytest.UsageError("PYLON_DATABASE_PATH must be set for tests.")

    db_path = Path(database_settings.path)

    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path

    db_path.parent.mkdir(parents=True, exist_ok=True)

    for path in (
        db_path,
        db_path.with_name(f"{db_path.name}-wal"),
        db_path.with_name(f"{db_path.name}-shm"),
    ):
        path.unlink(missing_ok=True)

    yield


@pytest_asyncio.fixture
async def clean_weight_tasks_db_table():
    async def _clean_weight_tasks_db_table() -> None:
        async with session_factory() as session:
            async with session.begin():
                await session.execute(delete(WeightTask))

    return _clean_weight_tasks_db_table


@pytest.fixture
def seed_running_weight_task_before_reschedule(monkeypatch):
    task_to_seed: list[WeightTask] = []
    real_reschedule_weight_tasks = lifecycle.reschedule_weight_tasks

    async def seed_then_reschedule(app):
        async with session_factory() as session:
            async with session.begin():
                await session.execute(delete(WeightTask))
                session.add_all(task_to_seed)
                await session.flush()

                base_created_at = datetime.now() - timedelta(seconds=len(task_to_seed))
                for index, task in enumerate(task_to_seed):
                    task.created_at = base_created_at + timedelta(seconds=index)

            for task in task_to_seed:
                await session.refresh(task)

        await real_reschedule_weight_tasks(app)

    monkeypatch.setattr(lifecycle, "reschedule_weight_tasks", seed_then_reschedule)

    return task_to_seed


@pytest.fixture(scope="session")
def test_app(mock_bt_contact_pool, mock_stores, setup_test_database):
    """
    Create a test Litestar app with the mock contact pool.
    """

    # Mock the bittensor contact pool lifespan to just set our mock pool.
    @asynccontextmanager
    async def mock_lifespan(app):
        app.state.bittensor_contact_pool = mock_bt_contact_pool
        yield

    # Mock the scheduler lifespan to prevent background task execution during tests
    @asynccontextmanager
    async def mock_scheduler_lifespan(app):
        yield

    with (
        patch.object(lifecycle, "bittensor_contact_pool_lifespan", mock_lifespan),
        patch.object(lifecycle, "scheduler_lifespan", mock_scheduler_lifespan),
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


@pytest.fixture
def mock_bt_client_factory(mock_bt_contact_pool):
    @asynccontextmanager
    async def _factory(identity_name: str | None = None):
        wallet = TEST_IDENTITIES[IdentityName(identity_name)].wallet if identity_name else None
        async with mock_bt_contact_pool.acquire(wallet=wallet) as router:
            yield router._main_contact
            router._main_contact.reset()
            router._archive_contact.reset()

    return _factory


@pytest_asyncio.fixture(scope="session")
async def shared_world(mock_bt_contact_pool) -> AsyncGenerator[SharedWorld]:
    async with AsyncExitStack() as stack:
        open_access_router = await stack.enter_async_context(mock_bt_contact_pool.acquire(wallet=None))

        id_contacts: dict[IdentityName, IdentityContacts] = {}
        for name, identity in TEST_IDENTITIES.items():
            router = await stack.enter_async_context(mock_bt_contact_pool.acquire(wallet=identity.wallet))
            id_contacts[name] = IdentityContacts(main=router._main_contact, archive=router._archive_contact)

        yield SharedWorld(
            open_access=IdentityContacts(
                main=open_access_router._main_contact,
                archive=open_access_router._archive_contact,
            ),
            identity_contacts=id_contacts,
            default_latest_block=default_latest_block(),
            default_neurons=default_neurons(
                own_commitment_hotkey=EXPECTED_IDENTITIES[IdentityName("sn24")].hotkey_ss58,
            ),
            default_subnet_states=default_subnet_states(
                own_commitment_hotkey=EXPECTED_IDENTITIES[IdentityName("sn24")].hotkey_ss58,
            ),
            default_commitments=default_commitments(),
            default_revealed_commitments=default_revealed_commitments(
                own_commitment_hotkey=EXPECTED_IDENTITIES[IdentityName("sn2")].hotkey_ss58,
            ),
            default_evm_key_associations=default_evm_assocations(),
        )


@pytest.fixture(autouse=True)
def reset_shared_world(shared_world: SharedWorld):
    shared_world.reset()
    shared_world.seed_defaults()
    yield
