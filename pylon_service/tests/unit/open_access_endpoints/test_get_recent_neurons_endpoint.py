import datetime as dt

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_503_SERVICE_UNAVAILABLE
from pylon_commons.models import Block, Neuron, SubnetNeurons
from pylon_commons.types import NetUid, Timestamp

from pylon_service.bittensor.recent.adapter import CacheKey, _CacheEntry
from pylon_service.settings import recent_objects_settings, settings
from tests.factories import BlockFactory, NeuronFactory


@pytest.fixture
def block(block_factory: BlockFactory) -> Block:
    BlockFactory.seed_random(1)
    return block_factory.build()


@pytest.fixture
def neurons(neuron_factory: NeuronFactory):
    NeuronFactory.seed_random(1)
    return neuron_factory.batch(2)


@pytest.fixture
def subnet_neurons(neurons: list[Neuron], block: Block):
    return SubnetNeurons(block=block, neurons={neuron.hotkey: neuron for neuron in neurons})


_ENDPOINT = "/api/v1/subnet/1/block/recent/neurons"


@pytest.mark.asyncio
async def test_get_recent_neurons_cache_missing(open_access_test_client, mock_recent_objects_store, snapshot_json):
    async with mock_recent_objects_store.behave.mock(get=[None]):
        response = await open_access_test_client.get(_ENDPOINT)

        assert response.status_code == HTTP_503_SERVICE_UNAVAILABLE
        assert response.json() == snapshot_json

    assert mock_recent_objects_store.behave.calls["get"] == [(CacheKey(SubnetNeurons, NetUid(1), None), None)]


@pytest.mark.asyncio
async def test_get_recent_neurons_cache_expired(
    open_access_test_client, mock_recent_objects_store, subnet_neurons, snapshot_json
):
    stale_blocks = recent_objects_settings.hard_limit_blocks + 1
    timestamp = Timestamp(int(dt.datetime.now().timestamp() - settings.block_duration_seconds * stale_blocks))
    cache_entry = _CacheEntry(data=subnet_neurons.model_dump_json(), timestamp=timestamp)
    async with mock_recent_objects_store.behave.mock(get=[cache_entry.model_dump_json().encode()]):
        response = await open_access_test_client.get(_ENDPOINT)

        assert response.status_code == HTTP_503_SERVICE_UNAVAILABLE
        assert response.json() == snapshot_json

    assert mock_recent_objects_store.behave.calls["get"] == [(CacheKey(SubnetNeurons, NetUid(1), None), None)]


@pytest.mark.asyncio
async def test_get_recent_neurons_success(
    open_access_test_client, mock_recent_objects_store, subnet_neurons, snapshot_json
):
    timestamp = Timestamp(int(dt.datetime.now().timestamp()))
    cache_entry = _CacheEntry(data=subnet_neurons.model_dump_json(), timestamp=timestamp)
    async with mock_recent_objects_store.behave.mock(get=[cache_entry.model_dump_json().encode()]):
        response = await open_access_test_client.get(_ENDPOINT)

        assert response.status_code == HTTP_200_OK
        assert response.json() == snapshot_json

    assert mock_recent_objects_store.behave.calls["get"] == [(CacheKey(SubnetNeurons, NetUid(1), None), None)]
