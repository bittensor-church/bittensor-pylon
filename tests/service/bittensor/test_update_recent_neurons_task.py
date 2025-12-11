import logging

import pytest

from pylon._internal.common.models import SubnetNeurons
from pylon._internal.common.types import NetUid, Timestamp
from pylon.service.bittensor.pool import BittensorClientPool
from pylon.service.bittensor.tasks import update_recent_neurons
from tests.behave import Behave
from tests.factories import BlockFactory, NeuronFactory
from tests.mock_bittensor_client import MockBittensorClient
from tests.mock_cache_manager import MockCacheManager


@pytest.mark.asyncio
async def test_update_recent_neurons_no_uids(
    open_access_mock_bt_client,
    mock_bt_client_pool: BittensorClientPool,
    mock_bt_cache_manager: MockCacheManager,
):
    await update_recent_neurons([], mock_bt_cache_manager, mock_bt_client_pool)
    assert len(open_access_mock_bt_client.calls) == 0


@pytest.mark.asyncio
async def test_update_recent_neurons_failed_to_get_block(
    open_access_mock_bt_client: MockBittensorClient,
    mock_bt_client_pool: BittensorClientPool,
    mock_bt_cache_manager: MockCacheManager,
    caplog,
):
    async with open_access_mock_bt_client.mock_behavior(get_latest_block=[Exception("Failed")] * 3):
        await update_recent_neurons([NetUid(1)], mock_bt_cache_manager, mock_bt_client_pool)

    assert caplog.messages[-1] == "Failed to fetch latest block. error: Failed"
    assert open_access_mock_bt_client.calls["get_latest_block"] == [(), (), ()]


@pytest.mark.asyncio
async def test_update_recent_neurons_failed_to_get_block_timestamp(
    open_access_mock_bt_client: MockBittensorClient,
    mock_bt_client_pool: BittensorClientPool,
    mock_bt_cache_manager: MockCacheManager,
    block_factory: BlockFactory,
    caplog,
):
    block = block_factory.build()
    async with open_access_mock_bt_client.mock_behavior(
        get_latest_block=[block],
        get_block_timestamp=[Exception("Failed")] * 3,
    ):
        await update_recent_neurons([NetUid(1)], mock_bt_cache_manager, mock_bt_client_pool)

    assert caplog.messages[-1] == "Failed to fetch block timestamp. error: Failed"
    assert open_access_mock_bt_client.calls["get_latest_block"] == [()]
    assert open_access_mock_bt_client.calls["get_block_timestamp"] == [(block,), (block,), (block,)]


@pytest.mark.asyncio
async def test_update_recent_neurons(
    caplog,
    open_access_mock_bt_client: MockBittensorClient,
    mock_bt_client_pool: BittensorClientPool,
    mock_bt_cache_manager: MockCacheManager,
    block_factory: BlockFactory,
    neuron_factory: NeuronFactory,
    behave: Behave,
):
    caplog.set_level(logging.INFO)
    block = block_factory.build()
    neurons = {n.hotkey: n for n in neuron_factory.batch(3)}
    subnet_neurons = SubnetNeurons(block=block, neurons=neurons)
    timestamp = Timestamp(123123123)

    def get_neurons_mock(netuid: NetUid, *args, **kwargs) -> SubnetNeurons:
        if netuid == NetUid(2):
            return subnet_neurons
        raise Exception("Failed")

    async with (
        open_access_mock_bt_client.mock_behavior(
            get_latest_block=[block],
            get_block_timestamp=[timestamp],
            get_neurons=[get_neurons_mock] * 4,
        ),
        behave.mock(set_recent_neurons=[None]),
    ):
        await update_recent_neurons([NetUid(1), NetUid(2)], mock_bt_cache_manager, mock_bt_client_pool)

    assert open_access_mock_bt_client.calls["get_latest_block"] == [()]
    assert open_access_mock_bt_client.calls["get_block_timestamp"] == [(block,)]
    assert open_access_mock_bt_client.calls["get_neurons"] == [
        (NetUid(1), block),
        (NetUid(2), block),
        (NetUid(1), block),
        (NetUid(1), block),
    ]
    assert behave.calls["set_recent_neurons"] == [(NetUid(2), timestamp, block, subnet_neurons)]
    assert caplog.messages == [
        "Starting recent neurons update for netuids: 1, 2",
        "Failed to fetch neurons. netuid: 1, error: Failed",
        "Failed to fetch neurons. netuid: 1, error: Failed",
        "Failed to fetch neurons. netuid: 1, error: Failed",
        "Finished recent neurons update. total: 2, succeeded: 1, failed: 1",
        "Failed to fetch recent neurons for netuids: 1",
    ]
