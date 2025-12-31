import datetime as dt

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_503_SERVICE_UNAVAILABLE

from pylon_client._internal.common.constants import BLOCK_PROCESSING_TIME
from pylon_client._internal.common.models import Block, Neuron, SubnetNeurons
from pylon_client._internal.common.types import HotkeyName, IdentityName, NetUid, Timestamp
from pylon_client.service.bittensor.recent.adapter import CacheKey, _CacheEntry
from pylon_client.service.identities import identities
from tests.factories import BlockFactory, NeuronFactory


@pytest.fixture
def block(block_factory: BlockFactory) -> Block:
    return block_factory.build()


@pytest.fixture
def neurons(neuron_factory: NeuronFactory):
    return neuron_factory.batch(2)


_ENDPOINT = "/api/v1/identity/sn1/subnet/1/block/recent/neurons"


@pytest.fixture
def subnet_neurons(neurons: list[Neuron], block: Block):
    return SubnetNeurons(block=block, neurons={neuron.hotkey: neuron for neuron in neurons})


@pytest.fixture
def wallet():
    return identities[IdentityName("sn1")].wallet


@pytest.mark.asyncio
async def test_get_recent_neurons_cache_missing(test_client, mock_recent_objects_store, wallet):
    async with mock_recent_objects_store.behave.mock(get=[None]):
        response = await test_client.get(_ENDPOINT)

        assert response.status_code == HTTP_503_SERVICE_UNAVAILABLE
        assert response.json() == {
            "status_code": HTTP_503_SERVICE_UNAVAILABLE,
            "detail": "Recent neurons data is not available. Cache update may not have finished "
            "yet or subnet may not be configured for caching recent objects.",
        }

    assert mock_recent_objects_store.behave.calls["get"] == [
        (CacheKey(SubnetNeurons, NetUid(1), HotkeyName(wallet.hotkey_str)), None)
    ]


@pytest.mark.asyncio
async def test_get_recent_neurons_cache_expired(test_client, mock_recent_objects_store, subnet_neurons, wallet):
    timestamp = Timestamp(int(dt.datetime.now().timestamp()) - BLOCK_PROCESSING_TIME * 50)  # 40 BLOCK hard limit set.
    cache_entry = _CacheEntry(data=subnet_neurons.model_dump_json(), timestamp=timestamp)
    async with mock_recent_objects_store.behave.mock(get=[cache_entry.model_dump_json().encode()]):
        response = await test_client.get(_ENDPOINT)

        assert response.status_code == HTTP_503_SERVICE_UNAVAILABLE
        assert response.json() == {
            "status_code": HTTP_503_SERVICE_UNAVAILABLE,
            "detail": "Recent neurons data is stale. Cache update may be failing.",
        }

    assert mock_recent_objects_store.behave.calls["get"] == [
        (CacheKey(SubnetNeurons, NetUid(1), HotkeyName(wallet.hotkey_str)), None)
    ]


@pytest.mark.asyncio
async def test_get_recent_neurons_success(test_client, mock_recent_objects_store, subnet_neurons, wallet):
    timestamp = Timestamp(int(dt.datetime.now().timestamp()))
    cache_entry = _CacheEntry(data=subnet_neurons.model_dump_json(), timestamp=timestamp)
    async with mock_recent_objects_store.behave.mock(get=[cache_entry.model_dump_json().encode()]):
        response = await test_client.get(_ENDPOINT)

        assert response.status_code == HTTP_200_OK
        assert response.json() == subnet_neurons.model_dump(mode="json")

    assert mock_recent_objects_store.behave.calls["get"] == [
        (CacheKey(SubnetNeurons, NetUid(1), HotkeyName(wallet.hotkey_str)), None)
    ]
