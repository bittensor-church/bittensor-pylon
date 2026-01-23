"""
Unit test specific fixtures.
"""

import pytest
import pytest_asyncio
from litestar.testing import AsyncTestClient

from pylon_service.stores import StoreName
from tests.mock_store import MockStore


@pytest_asyncio.fixture
async def test_client(test_app):
    """
    Create an async test client for the test app.
    """
    async with AsyncTestClient(app=test_app) as client:
        yield client


@pytest.fixture
def mock_recent_objects_store(mock_stores) -> MockStore:
    return mock_stores[StoreName.RECENT_OBJECTS]


@pytest.fixture(autouse=True)
def reset_mock_stores(mock_stores):
    yield
    for store in mock_stores.values():
        store.reset()
