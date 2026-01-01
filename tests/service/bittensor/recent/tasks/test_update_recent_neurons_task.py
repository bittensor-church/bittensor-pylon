import pytest

from pylon_client._internal.common.models import SubnetNeurons
from pylon_client._internal.common.types import NetUid, Timestamp
from pylon_client.service.bittensor.recent import SubnetContext, UpdateRecentNeurons
from pylon_client.service.bittensor.recent.adapter import CacheKey, _CacheEntry


@pytest.fixture
def update_task(mock_recent_objects_store, mock_bt_client_pool) -> UpdateRecentNeurons:
    return UpdateRecentNeurons(mock_recent_objects_store, mock_bt_client_pool)


@pytest.mark.asyncio
async def test_execute(
    mock_recent_objects_store,
    open_access_mock_bt_client,
    update_task,
    block_factory,
    neuron_factory,
):
    timestamp = Timestamp(123123123)
    block = block_factory.build()
    neurons = SubnetNeurons(block=block, neurons={neuron.hotkey: neuron for neuron in neuron_factory.batch(2)})
    context = SubnetContext(NetUid(1))

    async with (
        open_access_mock_bt_client.mock_behavior(
            get_latest_block=[block],
            get_block_timestamp=[timestamp],
            get_neurons=[neurons],
        ),
        mock_recent_objects_store.behave.mock(set=[None]),
    ):
        await update_task.execute(context)

    data = _CacheEntry(data=neurons.model_dump_json(), timestamp=timestamp).model_dump_json()

    assert open_access_mock_bt_client.calls["get_latest_block"] == [()]
    assert open_access_mock_bt_client.calls["get_block_timestamp"] == [(block,)]
    assert open_access_mock_bt_client.calls["get_neurons"] == [(NetUid(1), block)]
    assert mock_recent_objects_store.behave.calls["set"] == [(CacheKey(SubnetNeurons, NetUid(1), None), data, None)]
