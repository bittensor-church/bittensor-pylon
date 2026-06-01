from dirty_equals import IsInt
from pylon_commons.types import NetUid

from tests.integration.localchain.dev_accounts import DevAccount
from tests.integration.localchain.dev_evm_wallets import DevEvmWallet
from tests.matchers import SNAPSHOT_BLOCK

EXPECTED_EVM_ASSOCIATIONS = {
    "block": SNAPSHOT_BLOCK,
    "evm_associations": {
        DevAccount.ALICE.hotkey_ss58: {
            "hotkey": DevAccount.ALICE.hotkey_ss58,
            "evm_address": DevEvmWallet.ALICE.evm_address,
            "last_block_where_ownership_was_proven": IsInt(ge=0),
        },
        DevAccount.CHARLIE.hotkey_ss58: {
            "hotkey": DevAccount.CHARLIE.hotkey_ss58,
            "evm_address": DevEvmWallet.CHARLIE.evm_address,
            "last_block_where_ownership_was_proven": IsInt(ge=0),
        },
    },
}

EXPECTED_EVM_ASSOCIATIONS_EMPTY = {
    "block": SNAPSHOT_BLOCK,
    "evm_associations": {},
}


def test_get_latest_evm_associations_open_access_returns_data(pylon_client_factory):
    with pylon_client_factory("sn1") as client:
        response = client.unstable.open_access.get_latest_evm_associations(netuid=NetUid(1))
        assert response is not None
        assert response.model_dump() == EXPECTED_EVM_ASSOCIATIONS


def test_get_latest_evm_associations_identity_returns_data(pylon_client_factory):
    with pylon_client_factory("sn1") as client:
        response = client.unstable.identity.get_latest_evm_associations()
        assert response is not None
        assert response.model_dump() == EXPECTED_EVM_ASSOCIATIONS


def test_get_latest_evm_associations_open_access_returns_empty_map(pylon_client_factory):
    with pylon_client_factory("sn2") as client:
        response = client.unstable.open_access.get_latest_evm_associations(netuid=NetUid(2))
        assert response is not None
        assert response.model_dump() == EXPECTED_EVM_ASSOCIATIONS_EMPTY


def test_get_latest_evm_associations_identity_returns_empty_map(pylon_client_factory):
    with pylon_client_factory("sn2") as client:
        response = client.unstable.identity.get_latest_evm_associations()
        assert response is not None
        assert response.model_dump() == EXPECTED_EVM_ASSOCIATIONS_EMPTY
