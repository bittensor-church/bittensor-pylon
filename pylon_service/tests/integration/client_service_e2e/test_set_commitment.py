import time

import pytest
from pylon_client.artanis import (
    CommitmentDataHex,
    PylonNotFound,
)
from pylon_client.artanis.v1 import (
    GetCommitmentResponse,
    SetCommitmentResponse,
)

from tests.integration.localchain.dev_accounts import DevAccount


def test_set_commitment(pylon_client_factory):
    with pylon_client_factory("sn1") as client:
        with pytest.raises(PylonNotFound):
            client.v1.identity.get_own_commitment()

        set_response = client.v1.identity.set_commitment(CommitmentDataHex("0xdeadbeef"))

        assert isinstance(set_response, SetCommitmentResponse)
        # Wait a while for commitment to appear on the chain
        time.sleep(1)

        get_response = client.v1.identity.get_own_commitment()
        assert isinstance(get_response, GetCommitmentResponse)
        assert get_response.block.number > 0
        assert get_response.hotkey == DevAccount.ALICE.wallet.hotkey.ss58_address
        assert get_response.commitment == "0xdeadbeef"
