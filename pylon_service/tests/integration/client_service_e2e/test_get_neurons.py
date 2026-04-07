from pylon_client.artanis import NetUid, PylonClient
from pylon_client.artanis.v1 import GetNeuronsResponse


def test_get_neurons_at_latest_block_open_access(pylon_client: PylonClient):
    response = pylon_client.v1.open_access.get_latest_neurons(netuid=NetUid(1))

    assert isinstance(response, GetNeuronsResponse)
    assert response.block.number > 0
    assert response.block.hash
    assert len(response.neurons) > 0


def test_get_neurons_at_latest_block_identity(pylon_client: PylonClient):
    response = pylon_client.v1.identity.get_latest_neurons()

    assert isinstance(response, GetNeuronsResponse)
    assert response.block.number > 0
    assert response.block.hash
    assert len(response.neurons) > 0
