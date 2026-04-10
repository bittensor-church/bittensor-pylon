"""
Unit test specific fixtures.
"""

from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from litestar.testing import AsyncTestClient
from pylon_commons.types import IdentityName

from pylon_service.stores import StoreName
from tests.conftest import TEST_IDENTITIES
from tests.mock_store import MockStore


@pytest_asyncio.fixture
async def test_client(test_app):
    """
    Create an async test client for the test app.
    """
    async with AsyncTestClient(app=test_app) as client:
        yield client


@pytest.fixture
def identity_test_client_factory(test_app):
    @asynccontextmanager
    async def _factory(identity_name: str):
        token = TEST_IDENTITIES[IdentityName(identity_name)].token
        async with AsyncTestClient(app=test_app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            yield client

    return _factory


@pytest.fixture
def mock_recent_objects_store(mock_stores) -> MockStore:
    return mock_stores[StoreName.RECENT_OBJECTS]
