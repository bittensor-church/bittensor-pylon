import datetime as dt

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND

from pylon._internal.common.constants import BLOCK_PROCESSING_TIME
from pylon._internal.common.models import Block, Neuron, SubnetNeurons
from pylon._internal.common.types import Timestamp
from pylon.service.bittensor.cache.recent import _RecentCacheEntry
from tests.factories import BlockFactory, NeuronFactory


@pytest.fixture
def block(block_factory: BlockFactory) -> Block:
    return block_factory.build()


@pytest.fixture
def neurons(neuron_factory: NeuronFactory):
    return neuron_factory.batch(2)


@pytest.fixture
def subnet_neurons(neurons: list[Neuron], block: Block):
    return SubnetNeurons(block=block, neurons={neuron.hotkey: neuron for neuron in neurons})


_ENDPOINT = "/api/v1/subnet/1/block/recent/neurons"


@pytest.mark.asyncio
async def test_get_recent_neurons_cache_missing(test_client, behave):
    async with behave.mock(get=[None]):
        response = await test_client.get(_ENDPOINT)

        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.json() == {"status_code": 404, "detail": "Recent neurons not found."}

    assert behave.calls["get"] == [("recent_SubnetNeurons_1", None)]


@pytest.mark.asyncio
async def test_get_recent_neurons_cache_expired(test_client, behave, subnet_neurons):
    timestamp = Timestamp(int(dt.datetime.now().timestamp()) - BLOCK_PROCESSING_TIME * 50)  # 40 BLOCK hard limit set.
    cache_entry = _RecentCacheEntry[SubnetNeurons](entry=subnet_neurons, timestamp=timestamp)
    async with behave.mock(get=[cache_entry.model_dump_json().encode()]):
        response = await test_client.get(_ENDPOINT)

        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.json() == {"status_code": 404, "detail": "Recent neurons not found."}

    assert behave.calls["get"] == [("recent_SubnetNeurons_1", None)]


@pytest.mark.asyncio
async def test_get_recent_neurons_success(test_client, behave, subnet_neurons):
    timestamp = Timestamp(int(dt.datetime.now().timestamp()))
    cache_entry = _RecentCacheEntry[SubnetNeurons](entry=subnet_neurons, timestamp=timestamp)
    async with behave.mock(get=[cache_entry.model_dump_json().encode()]):
        response = await test_client.get(_ENDPOINT)

        assert response.status_code == HTTP_200_OK
        assert response.json() == subnet_neurons.model_dump(mode="json")

    assert behave.calls["get"] == [("recent_SubnetNeurons_1", None)]
