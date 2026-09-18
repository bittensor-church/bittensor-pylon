from __future__ import annotations

import enum
from functools import cache
from pathlib import Path
from tempfile import TemporaryDirectory

from bittensor.keyfiles import Keypair
from bittensor.wallet import Wallet


@cache
def _standalone_wallets_directory() -> TemporaryDirectory[str]:
    """
    Keep standalone chain setup wallets alive until process shutdown.
    """
    directory = TemporaryDirectory(prefix="pylon-dev-wallets-")
    generate_dev_wallets(Path(directory.name))
    return directory


def dev_wallets_directory() -> Path:
    """
    Resolve the wallet directory; pytest replaces this with its session-owned path.
    """
    return Path(_standalone_wallets_directory().name)


def generate_dev_wallets(directory: Path) -> None:
    """
    Write native v11 wallets for the well-known dev accounts into the supplied directory.
    """
    for account in DevAccount:
        wallet = Wallet(name=account.wallet_name, path=str(directory))
        keypair = Keypair.create_from_uri(account.uri)
        wallet.coldkey_file.set_keypair(keypair, encrypt=False)
        wallet.hotkey_file.set_keypair(keypair, encrypt=False)
        wallet.regenerate_coldkeypub(ss58_address=keypair.ss58_address)
        wallet.regenerate_hotkeypub(ss58_address=keypair.ss58_address)


class DevAccount(enum.Enum):
    """
    Well-known Substrate dev accounts available on localnet.

    Wallets are generated on demand with the v11 SDK in a temporary directory. Each account
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
        return Wallet(name=self.wallet_name, path=str(dev_wallets_directory()))

    @property
    def coldkey_ss58(self) -> str:
        return self.wallet.coldkeypub.ss58_address

    @property
    def hotkey_ss58(self) -> str:
        return self.wallet.hotkey.ss58_address
