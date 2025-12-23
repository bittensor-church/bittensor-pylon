"""
Shared fixtures for service endpoint tests.
"""

import pytest
import pytest_asyncio
from litestar.testing import AsyncTestClient

from pylon_client._internal.common.types import IdentityName
from pylon_client.service.bittensor.pool import BittensorClientPool
from pylon_client.service.identities import identities
from pylon_client.service.stores import StoreName
from tests.mock_bittensor_client import MockBittensorClient
from tests.mock_store import MockStore


@pytest_asyncio.fixture(loop_scope="session")
async def mock_bt_client_pool():
    """
    Create a mock Bittensor client pool.
    """
    async with BittensorClientPool(client_cls=MockBittensorClient, uri="ws://localhost:8000") as pool:
        yield pool


@pytest_asyncio.fixture
async def open_access_mock_bt_client(mock_bt_client_pool):
    async with mock_bt_client_pool.acquire(wallet=None) as client:
        yield client
        await client.reset_call_tracking()


@pytest_asyncio.fixture
async def sn1_mock_bt_client(mock_bt_client_pool):
    async with mock_bt_client_pool.acquire(wallet=identities[IdentityName("sn1")].wallet) as client:
        yield client
        await client.reset_call_tracking()


@pytest_asyncio.fixture
async def sn2_mock_bt_client(mock_bt_client_pool):
    async with mock_bt_client_pool.acquire(wallet=identities[IdentityName("sn2")].wallet) as client:
        yield client
        await client.reset_call_tracking()


@pytest.fixture
def mock_stores() -> dict[StoreName, MockStore]:
    return {
        StoreName.RECENT_OBJECTS: MockStore(),
    }


@pytest.fixture
def mock_recent_objects_store(mock_stores) -> MockStore:
    return mock_stores[StoreName.RECENT_OBJECTS]


@pytest_asyncio.fixture(loop_scope="session")
async def test_app(mock_bt_client_pool: MockBittensorClient, monkeypatch, mock_stores):
    """
    Create a test Litestar app with the mock client pool.
    """
    from contextlib import asynccontextmanager

    from pylon_client.service.main import create_app

    # Mock the bittensor_client lifespan to just set our mock client
    @asynccontextmanager
    async def mock_lifespan(app):
        app.state.bittensor_client_pool = mock_bt_client_pool
        yield

    # Mock the scheduler lifespan to prevent background task execution during tests
    @asynccontextmanager
    async def mock_scheduler_lifespan(app):
        yield

    # Replace the lifespans
    monkeypatch.setattr("pylon_client.service.lifespans.bittensor_client_pool", mock_lifespan)
    monkeypatch.setattr("pylon_client.service.lifespans.scheduler_lifespan", mock_scheduler_lifespan)
    monkeypatch.setattr("pylon_client.service.main.stores", mock_stores)

    app = create_app()
    app.debug = True  # Enable detailed error responses
    return app


@pytest_asyncio.fixture(loop_scope="session")
async def test_client(test_app):
    """
    Create an async test client for the test app.
    """
    async with AsyncTestClient(app=test_app) as client:
        yield client
