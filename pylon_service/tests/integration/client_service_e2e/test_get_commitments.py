import pytest
from pylon_client.artanis import CommitmentDataHex, Hotkey, NetUid, PylonClient, PylonNotFound
from pylon_client.artanis.v1 import GetCommitmentResponse, GetCommitmentsResponse

from tests.integration.localchain.dev_accounts import DevAccount


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


def test_get_commitment_by_hotkey(pylon_client: PylonClient):
    response = pylon_client.v1.open_access.get_commitment(
        netuid=NetUid(1), hotkey=Hotkey(DevAccount.CHARLIE.hotkey_ss58)
    )

    assert isinstance(response, GetCommitmentResponse)
    assert response.hotkey == DevAccount.CHARLIE.hotkey_ss58
    assert response.commitment == CommitmentDataHex(b"commitment-charlie".hex())
    assert response.block.number > 0
    assert response.block.hash


def test_get_commitment_for_hotkey_without_commitment(pylon_client: PylonClient):
    with pytest.raises(PylonNotFound):
        pylon_client.v1.open_access.get_commitment(netuid=NetUid(1), hotkey=Hotkey(DevAccount.BOB.hotkey_ss58))
