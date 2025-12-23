"""
Shared fixtures for service endpoint tests.
"""

import pytest
import pytest_asyncio
from litestar.testing import AsyncTestClient

from pylon._internal.common.types import IdentityName
from pylon.service.bittensor.pool import BittensorClientPool
from pylon.service.identities import identities
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
def mock_store(behave):
    return MockStore(behave)


@pytest_asyncio.fixture(loop_scope="session")
async def test_app(mock_bt_client_pool: MockBittensorClient, mock_store: MockStore, monkeypatch):
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

    # Mock the ap_scheduler lifespan to prevent background task execution during tests
    @asynccontextmanager
    async def mock_ap_scheduler(app):
        yield

    @asynccontextmanager
    async def mock_litestar_store(app):
        app.state.store = mock_store
        yield

    # Replace the lifespans
    monkeypatch.setattr("pylon.service.lifespans.bittensor_client_pool", mock_lifespan)
    monkeypatch.setattr("pylon.service.lifespans.ap_scheduler", mock_ap_scheduler)
    monkeypatch.setattr("pylon.service.lifespans.litestar_store", mock_litestar_store)

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
