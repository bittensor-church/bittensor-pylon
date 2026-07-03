import time

from pylon_client.artanis import CommitmentDataHex, PylonNotFound
from pylon_client.artanis.v1 import (
    GetCommitmentResponse,
    SetCommitmentResponse,
)
from pylon_commons.models import CommitmentKind

from tests.integration.localchain.dev_accounts import DevAccount


def test_set_commitment(pylon_client_factory):
    with pylon_client_factory("sn2") as client:
        set_response = client.v1.identity.set_commitment(CommitmentDataHex("0xdeadbeef"))

        assert isinstance(set_response, SetCommitmentResponse)

        get_response = client.v1.identity.get_own_commitment()
        assert isinstance(get_response, GetCommitmentResponse)
        assert get_response.block.number > 0
        assert get_response.hotkey == DevAccount.BOB.wallet.hotkey.ss58_address
        assert get_response.commitment == "0xdeadbeef"


def test_set_revealed_commitment_writes_readable_revealed_commitment(pylon_client_factory):
    with pylon_client_factory("sn2") as client:
        expected_commitment = "expected-revealed-commitment"
        set_response = client.unstable.identity.set_revealed_commitment(expected_commitment, 3)
        assert set_response.reveal_round > 0

        commitment_set = None
        for _ in range(15):
            try:
                get_response = client.unstable.identity.get_own_revealed_commitments()
            except PylonNotFound:
                time.sleep(1)
                continue
            commitment_set = next(
                (commitment for commitment in get_response.commitments if commitment.commitment == expected_commitment),
                None,
            )
            if commitment_set is not None:
                break
            time.sleep(1)

        assert commitment_set is not None
        assert commitment_set.hotkey == DevAccount.BOB.wallet.hotkey.ss58_address


def test_set_revealed_commitment_writes_readable_timelock_encrypted_commitment(pylon_client_factory):
    with pylon_client_factory("sn2") as client:
        expected_commitment = "expected-timelock-encrypted-commitment"
        set_response = client.unstable.identity.set_revealed_commitment(expected_commitment, 1000)
        assert set_response.reveal_round > 0

        get_response = client.unstable.identity.get_own_commitment()
        assert get_response is not None
        assert get_response.commitment.kind == CommitmentKind.TIMELOCK_ENCRYPTED
        assert get_response.commitment.reveal_round == set_response.reveal_round
