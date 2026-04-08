"""
Unit test specific fixtures.
"""

import json

import pytest
import pytest_asyncio
from litestar.stores.base import StorageObject
from litestar.stores.memory import MemoryStore
from litestar.testing import AsyncTestClient

from pylon_service.stores import StoreName
from tests.mock_store import MockStore

SESSION_ID = "test-session-id"


def seed_session(mock_stores: dict, identities: dict[str, dict]) -> None:
    """
    Seed the session store with identity data synchronously.

    Directly writes to MemoryStore._store to avoid async calls.
    """
    session_data = {"identities": identities}
    store = mock_stores[StoreName.SESSIONS]
    assert isinstance(store, MemoryStore)
    store._store[SESSION_ID] = StorageObject.new(data=json.dumps(session_data).encode(), expires_in=None)


@pytest_asyncio.fixture
async def test_client(test_app, mock_stores):
    seed_session(
        mock_stores,
        {
            "sn1": {"netuid": 1},
            "sn2": {"netuid": 2},
            "val": {"netuid": 11},
            "cm_all": {"netuid": 21},
            "cm_filtered": {"netuid": 22},
            "cm_empty": {"netuid": 23},
            "cm_own": {"netuid": 24},
        },
    )
    async with AsyncTestClient(app=test_app, cookies={"session": SESSION_ID}) as client:
        yield client


@pytest_asyncio.fixture
async def unauthenticated_test_client(test_app):
    async with AsyncTestClient(app=test_app) as client:
        yield client


@pytest.fixture
def mock_recent_objects_store(mock_stores) -> MockStore:
    return mock_stores[StoreName.RECENT_OBJECTS]
