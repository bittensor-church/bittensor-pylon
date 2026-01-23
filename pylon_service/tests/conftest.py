"""
Shared fixtures for all service tests (unit and pact).
"""

from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
import pytest_asyncio
from bittensor_wallet import Wallet
from polyfactory.pytest_plugin import register_fixture
from pylon_commons.types import IdentityName

from pylon_service import lifespans, main
from pylon_service.bittensor.pool import BittensorClientPool
from pylon_service.identities import identities
from pylon_service.main import create_app
from pylon_service.stores import StoreName
from tests.factories import BlockFactory, NeuronFactory
from tests.mock_bittensor_client import MockBittensorClient
from tests.mock_store import MockStore

register_fixture(BlockFactory)
register_fixture(NeuronFactory)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def mock_bt_client_pool():
    """
    Create a mock Bittensor client pool.
    """
    async with BittensorClientPool(client_cls=MockBittensorClient, uri="ws://localhost:8000") as pool:
        yield pool


@pytest.fixture(scope="session")
def mock_stores() -> dict[StoreName, MockStore]:
    return {
        StoreName.RECENT_OBJECTS: MockStore(),
    }


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
        patch.object(main, "stores", mock_stores),
    ):
        app = create_app()
        app.debug = True  # Enable detailed error responses
        yield app


@pytest.fixture
def wallet():
    return Wallet(path="tests/wallets", name="pylon", hotkey="pylon")


@pytest_asyncio.fixture
async def open_access_mock_bt_client(mock_bt_client_pool):
    async with mock_bt_client_pool.acquire(wallet=None) as client:
        yield client
        client.reset()


@pytest_asyncio.fixture
async def sn1_mock_bt_client(mock_bt_client_pool):
    async with mock_bt_client_pool.acquire(wallet=identities[IdentityName("sn1")].wallet) as client:
        yield client
        client.reset()


@pytest_asyncio.fixture
async def sn2_mock_bt_client(mock_bt_client_pool):
    async with mock_bt_client_pool.acquire(wallet=identities[IdentityName("sn2")].wallet) as client:
        yield client
        client.reset()
