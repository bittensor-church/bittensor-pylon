import time

import pytest
from pylon_client.artanis import (
    CommitmentDataHex,
    PylonClient,
    PylonNotFound,
)
from pylon_client.artanis.v1 import (
    GetCommitmentResponse,
    SetCommitmentResponse,
)


def test_set_commitment(pylon_client: PylonClient, wallet):
    with pytest.raises(PylonNotFound):
        pylon_client.v1.identity.get_own_commitment()

    set_response = pylon_client.v1.identity.set_commitment(CommitmentDataHex("0xdeadbeef"))

    assert isinstance(set_response, SetCommitmentResponse)
    # Wait a while for commitment to appear on the chain
    time.sleep(1)

    get_response = pylon_client.v1.identity.get_own_commitment()
    assert isinstance(get_response, GetCommitmentResponse)
    assert get_response.block.number > 0
    assert get_response.hotkey == wallet.hotkey.ss58_address
    assert get_response.commitment == "0xdeadbeef"
