from __future__ import annotations

from dataclasses import dataclass

from pylon_commons.types import HotkeyName, IdentityName, NetUid, PylonAuthToken, WalletName

TEST_ENV_FILE = "tests/.test-env"
TEST_OPEN_ACCESS_TOKEN = "test_token"


@dataclass(frozen=True)
class ExpectedIdentity:
    wallet_name: WalletName
    hotkey_name: HotkeyName
    netuid: NetUid
    token: PylonAuthToken
    hotkey_ss58: str


EXPECTED_IDENTITIES = {
    IdentityName("sn1"): ExpectedIdentity(
        wallet_name=WalletName("alice"),
        hotkey_name=HotkeyName("default"),
        netuid=NetUid(1),
        token=PylonAuthToken("sn1_token"),
        hotkey_ss58="5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY",
    ),
    IdentityName("sn1c"): ExpectedIdentity(
        wallet_name=WalletName("charlie"),
        hotkey_name=HotkeyName("default"),
        netuid=NetUid(1),
        token=PylonAuthToken("sn1c_token"),
        hotkey_ss58="5FLSigC9HGRKVhB9FiEo4Y3koPsNmBmLJbpXg2mp1hXcS59Y",
    ),
    IdentityName("sn2"): ExpectedIdentity(
        wallet_name=WalletName("bob"),
        hotkey_name=HotkeyName("default"),
        netuid=NetUid(2),
        token=PylonAuthToken("sn2_token"),
        hotkey_ss58="5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
    ),
    IdentityName("sn3"): ExpectedIdentity(
        wallet_name=WalletName("bob"),
        hotkey_name=HotkeyName("default"),
        netuid=NetUid(3),
        token=PylonAuthToken("sn3_token"),
        hotkey_ss58="5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
    ),
    IdentityName("sn4"): ExpectedIdentity(
        wallet_name=WalletName("charlie"),
        hotkey_name=HotkeyName("default"),
        netuid=NetUid(4),
        token=PylonAuthToken("sn4_token"),
        hotkey_ss58="5FLSigC9HGRKVhB9FiEo4Y3koPsNmBmLJbpXg2mp1hXcS59Y",
    ),
    IdentityName("sn11"): ExpectedIdentity(
        wallet_name=WalletName("charlie"),
        hotkey_name=HotkeyName("default"),
        netuid=NetUid(11),
        token=PylonAuthToken("sn11_token"),
        hotkey_ss58="5FLSigC9HGRKVhB9FiEo4Y3koPsNmBmLJbpXg2mp1hXcS59Y",
    ),
    IdentityName("sn21"): ExpectedIdentity(
        wallet_name=WalletName("dave"),
        hotkey_name=HotkeyName("default"),
        netuid=NetUid(21),
        token=PylonAuthToken("sn21_token"),
        hotkey_ss58="5DAAnrj7VHTznn2AWBemMuyBwZWs6FNFjdyVXUeYum3PTXFy",
    ),
    IdentityName("sn22"): ExpectedIdentity(
        wallet_name=WalletName("charlie"),
        hotkey_name=HotkeyName("default"),
        netuid=NetUid(22),
        token=PylonAuthToken("sn22_token"),
        hotkey_ss58="5FLSigC9HGRKVhB9FiEo4Y3koPsNmBmLJbpXg2mp1hXcS59Y",
    ),
    IdentityName("sn23"): ExpectedIdentity(
        wallet_name=WalletName("dave"),
        hotkey_name=HotkeyName("default"),
        netuid=NetUid(23),
        token=PylonAuthToken("sn23_token"),
        hotkey_ss58="5DAAnrj7VHTznn2AWBemMuyBwZWs6FNFjdyVXUeYum3PTXFy",
    ),
    IdentityName("sn24"): ExpectedIdentity(
        wallet_name=WalletName("bob"),
        hotkey_name=HotkeyName("default"),
        netuid=NetUid(24),
        token=PylonAuthToken("sn24_token"),
        hotkey_ss58="5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
    ),
    IdentityName("sn25"): ExpectedIdentity(
        wallet_name=WalletName("alice"),
        hotkey_name=HotkeyName("default"),
        netuid=NetUid(25),
        token=PylonAuthToken("sn25_token"),
        hotkey_ss58="5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY",
    ),
}


def assert_test_fixture_contract(*, settings, identities) -> None:
    errors: list[str] = []
    expected_names = list(EXPECTED_IDENTITIES)
    actual_names = list(settings.identities)

    if actual_names != expected_names:
        errors.append(f"expected settings.identities={expected_names!r}, got {actual_names!r}")

    if settings.open_access_token != TEST_OPEN_ACCESS_TOKEN:
        errors.append(
            f"expected settings.open_access_token={TEST_OPEN_ACCESS_TOKEN!r}, got {settings.open_access_token!r}"
        )

    actual_identity_names = list(identities)
    if actual_identity_names != expected_names:
        errors.append(f"expected loaded identities={expected_names!r}, got {actual_identity_names!r}")

    for identity_name, expected in EXPECTED_IDENTITIES.items():
        identity = identities.get(identity_name)
        if identity is None:
            errors.append(f"missing identity {identity_name!r} in loaded identities")
            continue

        actual_fields = {
            "wallet_name": identity.wallet_name,
            "hotkey_name": identity.hotkey_name,
            "netuid": identity.netuid,
            "token": identity.token,
        }
        expected_fields = {
            "wallet_name": expected.wallet_name,
            "hotkey_name": expected.hotkey_name,
            "netuid": expected.netuid,
            "token": expected.token,
        }
        if actual_fields != expected_fields:
            errors.append(f"identity {identity_name!r} mismatch: expected {expected_fields!r}, got {actual_fields!r}")

        wallet = getattr(identity, "wallet", None)
        if wallet is not None:
            try:
                actual_hotkey = wallet.hotkey.ss58_address
            except Exception as exc:
                errors.append(
                    f"identity {identity_name!r} wallet could not resolve hotkey: {type(exc).__name__}: {exc}"
                )
            else:
                if actual_hotkey != expected.hotkey_ss58:
                    errors.append(
                        f"identity {identity_name!r} hotkey mismatch: expected {expected.hotkey_ss58!r}, got {actual_hotkey!r}"
                    )

    if errors:
        details = "\n".join(f"- {error}" for error in errors)
        raise RuntimeError(
            f"{TEST_ENV_FILE} fixture contract mismatch.\n"
            "Tests in this package depend on these env-backed identities and tokens.\n"
            "The run was halted early because otherwise you would get misleading downstream failures.\n"
            f"Expected contract source: {TEST_ENV_FILE}\n"
            f"{details}"
        )
