"""
Fixtures for transport-seam endpoint tests.
"""

from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from litestar.testing import AsyncTestClient
from pylon_commons.types import BittensorNetwork

from pylon_service import lifespans, main
from pylon_service.bittensor.pool import BittensorClientPool
from pylon_service.main import create_app
from pylon_service.stores import StoreName
from tests.mock_store import MockStore


# These fixtures intentionally duplicate a subset of the older test setup.
# This directory is the start of a gradual migration away from pylon_service/tests/,
# so these tests must not inherit the shared MockBittensorClient-based pool seam.


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def bt_client_pool():
    async with BittensorClientPool(
        uri=BittensorNetwork("ws://localhost:8000"),
        archive_uri=BittensorNetwork("ws://localhost:8001"),
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
def test_app(bt_client_pool, mock_stores):
    @asynccontextmanager
    async def mock_lifespan(app):
        app.state.bittensor_client_pool = bt_client_pool
        yield

    @asynccontextmanager
    async def mock_scheduler_lifespan(app):
        yield

    with (
        pytest.MonkeyPatch.context() as monkeypatch,
    ):
        monkeypatch.setattr(lifespans, "bittensor_client_pool", mock_lifespan)
        monkeypatch.setattr(lifespans, "scheduler_lifespan", mock_scheduler_lifespan)
        monkeypatch.setattr(main, "stores", {**mock_stores})

        app = create_app()
        app.response_cache_config.cache_response_filter = lambda _, __: False
        app.debug = True
        yield app


@pytest_asyncio.fixture
async def test_client(test_app):
    async with AsyncTestClient(app=test_app) as client:
        yield client
