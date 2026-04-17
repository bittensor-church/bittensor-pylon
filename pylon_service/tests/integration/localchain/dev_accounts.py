from __future__ import annotations

import enum
from pathlib import Path

from bittensor_wallet import Wallet

WALLETS_DIR = Path(__file__).resolve().parents[2] / "wallets"


class DevAccount(enum.Enum):
    """
    Well-known Substrate dev accounts available on localnet.

    Wallets are pre-generated in tests/wallets/ directory. Each account
    has identical coldkey and hotkey (derived from the same URI).
    """

    ALICE = "alice"
    BOB = "bob"
    CHARLIE = "charlie"
    DAVE = "dave"

    @property
    def wallet_name(self) -> str:
        return self.value

    @property
    def uri(self) -> str:
        return f"//{self.value.capitalize()}"

    @property
    def wallet(self) -> Wallet:
        return Wallet(name=self.wallet_name, path=str(WALLETS_DIR))

    @property
    def coldkey_ss58(self) -> str:
        return self.wallet.coldkeypub.ss58_address

    @property
    def hotkey_ss58(self) -> str:
        return self.wallet.hotkey.ss58_address


SUDO_WALLET = DevAccount.ALICE.wallet
