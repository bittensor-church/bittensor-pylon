"""
Shared fixtures for service endpoint tests.
"""

import pytest
import pytest_asyncio
from litestar.testing import AsyncTestClient

from pylon._internal.common.types import IdentityName
from pylon.service.bittensor.pool import BittensorClientPool
from pylon.service.identities import identities
from tests.behave import Behave
from tests.mock_bittensor_client import MockBittensorClient
from tests.mock_cache_manager import MockCacheManager


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
def mock_bt_cache_manager(behave: Behave) -> MockCacheManager:
    return MockCacheManager(behave)


@pytest_asyncio.fixture(loop_scope="session")
async def test_app(
    mock_bt_client_pool: MockBittensorClient,
    mock_bt_cache_manager: MockCacheManager,
    monkeypatch,
):
    """
    Create a test Litestar app with the mock client pool.
    """
    from contextlib import asynccontextmanager

    from pylon.service.main import create_app

    # Mock the bittensor_client lifespan to just set our mock client
    @asynccontextmanager
    async def mock_lifespan(app):
        app.state.bittensor_client_pool = mock_bt_client_pool
        yield

    # Mock the background lifespan to prevent background task execution during tests
    @asynccontextmanager
    async def mock_background(app):
        yield

    # Always use an in-memory store during tests to keep tests
    # clear of dependency when we switch the implementation.
    @asynccontextmanager
    async def mock_cache_manager_lifespan(app):
        app.state.cache_manager = mock_bt_cache_manager
        yield

    # Replace the lifespans
    monkeypatch.setattr("pylon.service.lifespans.bittensor_client_pool", mock_lifespan)
    monkeypatch.setattr("pylon.service.lifespans.background_tasks", mock_background)
    monkeypatch.setattr("pylon.service.lifespans.bittensor_cache_manager", mock_cache_manager_lifespan)

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
