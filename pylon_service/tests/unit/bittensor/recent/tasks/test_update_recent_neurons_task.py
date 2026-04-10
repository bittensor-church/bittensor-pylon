import pytest
from pylon_commons.models import SubnetNeurons
from pylon_commons.types import NetUid, Timestamp

from pylon_service.bittensor.recent import SubnetContext, UpdateRecentNeurons
from pylon_service.bittensor.recent.adapter import CacheKey, _CacheEntry


@pytest.fixture
def update_task(mock_recent_objects_store, mock_bt_contact_pool) -> UpdateRecentNeurons:
    return UpdateRecentNeurons(mock_recent_objects_store, mock_bt_contact_pool)


@pytest.mark.asyncio
async def test_execute(
    mock_recent_objects_store,
    mock_bt_client_factory,
    update_task,
    block_factory,
    neuron_factory,
):
    timestamp = Timestamp(123123123)
    block = block_factory.build()
    neurons = SubnetNeurons(block=block, neurons={neuron.hotkey: neuron for neuron in neuron_factory.batch(2)})
    context = SubnetContext(NetUid(1))

    async with mock_bt_client_factory() as mock_client:
        async with (
            mock_client.mock_behavior(
                get_latest_block=[block],
                get_block_timestamp=[timestamp],
                get_neurons=[neurons],
            ),
            mock_recent_objects_store.behave.mock(set=[None]),
        ):
            await update_task.execute(context)

        data = _CacheEntry(data=neurons.model_dump_json(), timestamp=timestamp).model_dump_json()

        assert mock_client.calls["get_latest_block"] == [(), (), ()]
        assert mock_client.calls["get_block_timestamp"] == [(block,)]
        assert mock_client.calls["get_neurons"] == [(NetUid(1), block)]
        assert mock_recent_objects_store.behave.calls["set"] == [(CacheKey(SubnetNeurons, NetUid(1), None), data, None)]
