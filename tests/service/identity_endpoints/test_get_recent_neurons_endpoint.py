"""
Tests for the GET /subnet/{netuid}/neurons/recent endpoint.
"""

import datetime as dt

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient

from pylon._internal.common.models import Block, SubnetNeurons
from pylon._internal.common.types import NetUid, Timestamp
from pylon.service.bittensor.cache.models import CacheEntry
from tests.behave import Behave
from tests.factories import BlockFactory, NeuronFactory
from tests.mock_cache_manager import MockCacheManager


@pytest.fixture
def block(block_factory: BlockFactory) -> Block:
    return block_factory.build()


@pytest.fixture
def neurons(neuron_factory: NeuronFactory):
    return neuron_factory.batch(2)


@pytest.fixture
def subnet_neurons(neurons, block):
    return SubnetNeurons(block=block, neurons={neuron.hotkey: neuron for neuron in neurons})


@pytest.fixture
def cache_entry(subnet_neurons, block) -> CacheEntry[SubnetNeurons]:
    now = dt.datetime.now(tz=dt.UTC).timestamp()
    timestamp = Timestamp(int(now))
    return CacheEntry(entry=subnet_neurons, block=block, cached_at=timestamp)


@pytest.mark.asyncio
async def test_get_recent_neurons_success(
    test_client: AsyncTestClient,
    cache_entry: CacheEntry[SubnetNeurons],
    mock_bt_cache_manager: MockCacheManager,
    behave: Behave,
):
    async with behave.mock(get_recent_neurons=[cache_entry]):
        response = await test_client.get("/api/v1/identity/sn1/subnet/1/neurons/recent")

    assert response.status_code == HTTP_200_OK, response.content
    assert response.json() == cache_entry.entry.model_dump(mode="json")
    assert behave.calls["get_recent_neurons"] == [(NetUid(1),)]


@pytest.mark.asyncio
async def test_get_recent_neurons_not_found(
    test_client: AsyncTestClient,
    mock_bt_cache_manager: MockCacheManager,
    behave: Behave,
):
    async with behave.mock(get_recent_neurons=[None]):
        response = await test_client.get("/api/v1/identity/sn1/subnet/1/neurons/recent")

    assert response.status_code == HTTP_404_NOT_FOUND, response.content
    assert response.json() == {
        "status_code": HTTP_404_NOT_FOUND,
        "detail": "Recent neurons not found.",
    }
    assert behave.calls["get_recent_neurons"] == [(NetUid(1),)]
