from __future__ import annotations

import enum

from eth_account import Account
from eth_account.signers.local import LocalAccount
from pylon_commons.types import EvmAddress

# enable creating an account from mnemonic
Account.enable_unaudited_hdwallet_features()


class DevEvmWallet(enum.Enum):
    """
    Deterministic EVM test wallets.
    """

    ALICE = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
    BOB = "legal winner thank year wave sausage worth useful legal winner thank yellow"
    CHARLIE = "letter advice cage absurd amount doctor acoustic avoid letter advice cage above"
    DAVE = "zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo wrong"

    @property
    def mnemonic(self) -> str:
        return self.value

    @property
    def wallet(self) -> LocalAccount:
        if self not in _EVM_WALLET_CACHE:
            _EVM_WALLET_CACHE[self] = Account.from_mnemonic(self.mnemonic)
        return _EVM_WALLET_CACHE[self]

    @property
    def evm_address(self) -> EvmAddress:
        return EvmAddress(self.wallet.address.lower())


_EVM_WALLET_CACHE: dict[DevEvmWallet, LocalAccount] = {}
