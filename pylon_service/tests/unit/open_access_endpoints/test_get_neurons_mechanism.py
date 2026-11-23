"""
Tests for the optional mechanism_id query parameter of the open-access neuron endpoints.
"""

import pytest
from litestar.status_codes import HTTP_200_OK
from litestar.testing import AsyncTestClient
from pylon_commons.models import SubnetNeurons
from pylon_commons.types import Incentive, MechanismId, Timestamp

from pylon_service.bittensor.contact import MechanismMetrics
from tests.factories import BlockFactory, NeuronFactory


@pytest.mark.asyncio
async def test_open_access_latest_neurons_default_mechanism_is_unchanged(
    open_access_test_client: AsyncTestClient, mock_bt_client_factory
):
    """
    Test that a request without mechanism_id reads no mechanism storage and answers for mechanism 0.
    """
    block = BlockFactory.build()
    neuron = NeuronFactory.build(uid=0)
    subnet_neurons = SubnetNeurons(block=block, neurons={neuron.hotkey: neuron})
    async with mock_bt_client_factory() as mock_client:
        async with mock_client.mock_behavior(get_latest_block=[block], get_neurons=[subnet_neurons]):
            response = await open_access_test_client.get("/api/v1/subnet/1/block/latest/neurons")
        assert "get_mechanism_metrics" not in mock_client.calls

    assert response.status_code == HTTP_200_OK, response.content
    assert response.json() == subnet_neurons.model_dump(mode="json")


@pytest.mark.asyncio
async def test_open_access_latest_neurons_for_mechanism_overlays_mechanism_values(
    open_access_test_client: AsyncTestClient, mock_bt_client_factory
):
    """
    Test that a mechanism's incentive and last update replace the neuron info values.
    """
    block = BlockFactory.build()
    neuron = NeuronFactory.build(uid=0, incentive=Incentive(0.1), last_update=Timestamp(10))
    subnet_neurons = SubnetNeurons(block=block, neurons={neuron.hotkey: neuron})
    metrics = MechanismMetrics(incentives=[32768], last_updates=[42])
    async with mock_bt_client_factory() as mock_client:
        async with mock_client.mock_behavior(
            get_latest_block=[block, block], get_neurons=[subnet_neurons], get_mechanism_metrics=[metrics]
        ):
            response = await open_access_test_client.get(
                "/api/v1/subnet/1/block/latest/neurons", params={"mechanism_id": 1}
            )
        assert mock_client.calls["get_mechanism_metrics"] == [(1, 1, block)]

    expected = SubnetNeurons(
        block=block,
        mechanism_id=MechanismId(1),
        neurons={
            neuron.hotkey: neuron.model_copy(
                update={"incentive": Incentive(32768 / 65535), "last_update": Timestamp(42)}
            )
        },
    )
    assert response.status_code == HTTP_200_OK, response.content
    assert response.json() == expected.model_dump(mode="json")
