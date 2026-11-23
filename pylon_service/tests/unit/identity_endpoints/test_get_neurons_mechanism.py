"""
Tests for the optional mechanism_id query parameter of the v1 identity neuron endpoints.

v1 reuses the unstable handlers, so the full coverage lives in the unstable tests.
"""

import pytest
from litestar.status_codes import HTTP_200_OK
from pylon_commons.models import SubnetNeurons
from pylon_commons.types import Incentive, MechanismId, Timestamp

from pylon_service.bittensor.contact import MechanismMetrics
from tests.factories import BlockFactory, NeuronFactory


@pytest.mark.asyncio
async def test_latest_neurons_for_mechanism_overlays_mechanism_values(
    mock_bt_client_factory, identity_test_client_factory
):
    """
    Test that a mechanism's incentive and last update replace the neuron info values.
    """
    block = BlockFactory.build()
    neuron = NeuronFactory.build(uid=0, incentive=Incentive(0.1), last_update=Timestamp(10))
    subnet_neurons = SubnetNeurons(block=block, neurons={neuron.hotkey: neuron})
    metrics = MechanismMetrics(incentives=[32768], last_updates=[42])
    async with mock_bt_client_factory("sn1") as mock_client:
        async with mock_client.mock_behavior(
            get_latest_block=[block, block], get_neurons=[subnet_neurons], get_mechanism_metrics=[metrics]
        ):
            async with identity_test_client_factory("sn1") as client:
                response = await client.get(
                    "/api/v1/identity/sn1/subnet/1/block/latest/neurons", params={"mechanism_id": 1}
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
