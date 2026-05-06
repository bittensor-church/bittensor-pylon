import pytest
from pylon_client.artanis import CommitmentDataHex, Hotkey, NetUid, PylonNotFound
from pylon_client.artanis.unstable import GetAllRevealedCommitmentsResponse, GetRevealedCommitmentsResponse
from pylon_client.artanis.v1 import GetCommitmentResponse, GetCommitmentsResponse

from tests.integration.localchain.dev_accounts import DevAccount


def test_get_commitments_open_access(pylon_client_factory):
    with pylon_client_factory("sn1") as client:
        response = client.v1.open_access.get_commitments(netuid=NetUid(1))

        assert isinstance(response, GetCommitmentsResponse)
        assert response.block.number > 0
        assert response.block.hash
        assert len(response.commitments) > 0


def test_get_commitments_identity(pylon_client_factory):
    with pylon_client_factory("sn1") as client:
        response = client.v1.identity.get_commitments()

        assert isinstance(response, GetCommitmentsResponse)
        assert response.block.number > 0
        assert response.block.hash
        assert len(response.commitments) > 0


def test_get_commitment_by_hotkey(pylon_client_factory):
    with pylon_client_factory("sn1") as client:
        response = client.v1.open_access.get_commitment(netuid=NetUid(1), hotkey=Hotkey(DevAccount.CHARLIE.hotkey_ss58))

        assert isinstance(response, GetCommitmentResponse)
        assert response.hotkey == DevAccount.CHARLIE.hotkey_ss58
        assert response.commitment == CommitmentDataHex(b"commitment-charlie".hex())
        assert response.block.number > 0
        assert response.block.hash


def test_get_own_commitment_identity(pylon_client_factory):
    with pylon_client_factory("sn1c") as client:
        response = client.v1.identity.get_own_commitment()

        assert isinstance(response, GetCommitmentResponse)
        assert response.hotkey == DevAccount.CHARLIE.hotkey_ss58
        assert response.commitment == CommitmentDataHex(b"commitment-charlie".hex())
        assert response.block.number > 0
        assert response.block.hash


def test_get_commitment_for_hotkey_without_commitment(pylon_client_factory):
    with pylon_client_factory("sn1") as client:
        with pytest.raises(PylonNotFound):
            client.v1.open_access.get_commitment(netuid=NetUid(1), hotkey=Hotkey(DevAccount.BOB.hotkey_ss58))


def test_get_own_commitment_without_commitment_identity(pylon_client_factory):
    with pylon_client_factory("sn11") as client:
        with pytest.raises(PylonNotFound):
            client.v1.identity.get_own_commitment()


def test_get_all_revealed_commitments_open_access(pylon_client_factory):
    with pylon_client_factory("sn1") as client:
        response = client.unstable.open_access.get_all_revealed_commitments(netuid=NetUid(1))
        assert isinstance(response, GetAllRevealedCommitmentsResponse)
        assert response.block.number > 0
        assert response.block.hash
        assert len(response.commitments) > 0


def test_get_revealed_commitments_for_hotkey_open_access(pylon_client_factory):
    with pylon_client_factory("sn1") as client:
        response = client.unstable.open_access.get_revealed_commitments(
            netuid=NetUid(1), hotkey=Hotkey(DevAccount.ALICE.hotkey_ss58)
        )

        assert isinstance(response, GetRevealedCommitmentsResponse)
        assert response.block.number > 0
        assert response.block.hash
        assert len(response.commitments) > 0
        assert response.commitments[0].hotkey == DevAccount.ALICE.hotkey_ss58


def test_get_all_revealed_commitments_identity(pylon_client_factory):
    with pylon_client_factory("sn1") as client:
        response = client.unstable.identity.get_all_revealed_commitments()

        assert isinstance(response, GetAllRevealedCommitmentsResponse)
        assert response.block.number > 0
        assert response.block.hash
        assert len(response.commitments) > 0


def test_get_revealed_commitments_for_hotkey_identity(pylon_client_factory):
    with pylon_client_factory("sn1") as client:
        response = client.unstable.identity.get_revealed_commitments(hotkey=Hotkey(DevAccount.BOB.hotkey_ss58))

        assert isinstance(response, GetRevealedCommitmentsResponse)
        assert response.block.number > 0
        assert response.block.hash
        assert len(response.commitments) > 0
        assert response.commitments[0].hotkey == DevAccount.BOB.hotkey_ss58


def test_get_own_revealed_commitments_identity(pylon_client_factory):
    with pylon_client_factory("sn1") as client:
        response = client.unstable.identity.get_own_revealed_commitments()

        assert isinstance(response, GetRevealedCommitmentsResponse)
        assert response.block.number > 0
        assert response.block.hash
        assert len(response.commitments) > 0
        assert response.commitments[0].hotkey == DevAccount.ALICE.hotkey_ss58


def test_get_revealed_commitments_for_hotkey_identity_without_commitment(pylon_client_factory):
    with pylon_client_factory("sn1") as client:
        with pytest.raises(PylonNotFound):
            client.unstable.identity.get_revealed_commitments(hotkey=Hotkey(DevAccount.CHARLIE.hotkey_ss58))


def test_get_own_revealed_commitments_without_commitment_identity(pylon_client_factory):
    with pylon_client_factory("sn1c") as client:
        with pytest.raises(PylonNotFound):
            client.unstable.identity.get_own_revealed_commitments()
