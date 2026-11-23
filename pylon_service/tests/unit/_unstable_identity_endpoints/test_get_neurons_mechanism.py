"""
Tests for the optional mechanism_id query parameter of the unstable identity neuron endpoints.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from pylon_commons.models import SubnetNeurons
from pylon_commons.types import Incentive, MechanismId, Timestamp

from pylon_service.bittensor.contact import MechanismMetrics
from tests.factories import BlockFactory, NeuronFactory


def _neurons(block):
    neuron = NeuronFactory.build(uid=0, incentive=Incentive(0.1), last_update=Timestamp(10))
    return neuron, SubnetNeurons(block=block, neurons={neuron.hotkey: neuron})


@pytest.mark.asyncio
async def test_latest_neurons_default_mechanism_is_unchanged(mock_bt_client_factory, identity_test_client_factory):
    """
    Test that a request without mechanism_id reads no mechanism storage and answers for mechanism 0.
    """
    block = BlockFactory.build()
    _, subnet_neurons = _neurons(block)
    async with mock_bt_client_factory("sn1") as mock_client:
        async with mock_client.mock_behavior(get_latest_block=[block], get_neurons=[subnet_neurons]):
            async with identity_test_client_factory("sn1") as client:
                response = await client.get("/api/_unstable/identity/sn1/subnet/1/block/latest/neurons")
        assert "get_mechanism_metrics" not in mock_client.calls

    assert response.status_code == HTTP_200_OK, response.content
    assert response.json() == subnet_neurons.model_dump(mode="json")


@pytest.mark.asyncio
async def test_latest_neurons_for_mechanism_overlays_mechanism_values(
    mock_bt_client_factory, identity_test_client_factory
):
    """
    Test that a mechanism's incentive and last update replace the neuron info values.
    """
    block = BlockFactory.build()
    neuron, subnet_neurons = _neurons(block)
    metrics = MechanismMetrics(incentives=[32768], last_updates=[42])
    async with mock_bt_client_factory("sn1") as mock_client:
        async with mock_client.mock_behavior(
            get_latest_block=[block, block], get_neurons=[subnet_neurons], get_mechanism_metrics=[metrics]
        ):
            async with identity_test_client_factory("sn1") as client:
                response = await client.get(
                    "/api/_unstable/identity/sn1/subnet/1/block/latest/neurons", params={"mechanism_id": 1}
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


@pytest.mark.asyncio
async def test_neurons_at_block_for_mechanism(mock_bt_client_factory, identity_test_client_factory):
    """
    Test that the at-block endpoint reads the mechanism at the requested block; missing UIDs read as 0.
    """
    block = BlockFactory.build(number=123)
    neuron, subnet_neurons = _neurons(block)
    metrics = MechanismMetrics(incentives=[], last_updates=[])
    async with mock_bt_client_factory("sn1") as mock_client:
        async with mock_client.mock_behavior(
            get_block=[block], get_neurons=[subnet_neurons], get_mechanism_metrics=[metrics]
        ):
            async with identity_test_client_factory("sn1") as client:
                response = await client.get(
                    "/api/_unstable/identity/sn1/subnet/1/block/123/neurons", params={"mechanism_id": 1}
                )
        assert mock_client.calls["get_mechanism_metrics"] == [(1, 1, block)]

    expected = SubnetNeurons(
        block=block,
        mechanism_id=MechanismId(1),
        neurons={neuron.hotkey: neuron.model_copy(update={"incentive": Incentive(0.0), "last_update": Timestamp(0)})},
    )
    assert response.status_code == HTTP_200_OK, response.content
    assert response.json() == expected.model_dump(mode="json")


@pytest.mark.asyncio
async def test_unknown_mechanism_returns_404_without_reading_neurons(
    mock_bt_client_factory, identity_test_client_factory
):
    """
    Test that a mechanism the subnet does not have returns 404 before neurons are read.
    """
    block = BlockFactory.build()
    async with mock_bt_client_factory("sn1") as mock_client:
        async with mock_client.mock_behavior(get_latest_block=[block, block], get_mechanism_metrics=[None]):
            async with identity_test_client_factory("sn1") as client:
                response = await client.get(
                    "/api/_unstable/identity/sn1/subnet/1/block/latest/neurons", params={"mechanism_id": 5}
                )
        assert "get_neurons" not in mock_client.calls

    assert response.status_code == HTTP_404_NOT_FOUND, response.content
    assert response.json() == {"status_code": 404, "detail": "Mechanism 5 not found on subnet 1."}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        pytest.param("/api/_unstable/identity/sn1/subnet/1/block/latest/neurons?mechanism_id=-1", id="latest"),
        pytest.param("/api/_unstable/identity/sn1/subnet/1/block/123/neurons?mechanism_id=-1", id="at_block"),
    ],
)
async def test_negative_mechanism_returns_400(url, mock_bt_client_factory, identity_test_client_factory):
    """
    Test that a negative mechanism_id is rejected before anything is read from the chain.
    """
    async with mock_bt_client_factory("sn1") as mock_client:
        async with identity_test_client_factory("sn1") as client:
            response = await client.get(url)
        assert dict(mock_client.calls) == {}

    assert response.status_code == HTTP_400_BAD_REQUEST, response.content
    assert response.json() == {
        "status_code": 400,
        "detail": f"Validation failed for GET {url}",
        "extra": [{"message": "Expected `int` >= 0", "key": "mechanism_id", "source": "query"}],
    }
