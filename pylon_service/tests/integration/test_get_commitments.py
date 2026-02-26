from pylon_client.artanis import NetUid, PylonClient
from pylon_client.artanis.v1 import GetCommitmentsResponse


def test_get_commitments_open_access(pylon_client: PylonClient):
    response = pylon_client.v1.open_access.get_commitments(netuid=NetUid(1))

    assert isinstance(response, GetCommitmentsResponse)
    assert response.block.number > 0
    assert response.block.hash
    assert len(response.commitments) > 0


def test_get_commitments_identity(pylon_client: PylonClient):
    response = pylon_client.v1.identity.get_commitments()

    assert isinstance(response, GetCommitmentsResponse)
    assert response.block.number > 0
    assert response.block.hash
    assert len(response.commitments) > 0
