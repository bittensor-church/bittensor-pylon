"""
Legacy wallet generation -> PylonClient -> Pylon HTTP service -> signed localchain extrinsic.

Each wallet format gets its own subnet on the shared E2E localchain.
"""

import json
import subprocess
import sys

import pytest
import pytest_asyncio
from bittensor.wallet import Wallet
from pylon_client.artanis import CommitmentDataHex, Config, IdentityName, PylonAuthToken, PylonClient, PylonTimeout

from tests.integration.containers import PylonServiceContainer
from tests.integration.localchain.dev_accounts import DevAccount


@pytest.fixture(
    scope="module",
    params=[
        pytest.param("legacy", id="legacy_without_crypto_type"),
        pytest.param("10.5", id="bittensor_10_5_cli"),
    ],
)
def generated_legacy_wallet(request, tmp_path_factory):
    """
    Create each legacy format with its producer, independently of the reader under test.
    """
    path = tmp_path_factory.mktemp(f"wallet_{request.param}")
    name = "compatibility"
    packages = {
        "legacy": ["bittensor-wallet==4.0.1"],
        "10.5": [
            "bittensor[cli]==10.5.0",
            "bittensor-cli==9.22.0",
            "bittensor-wallet==4.1.0",
        ],
    }
    command = ["uv", "run", "--isolated", "--no-project", "--python", sys.executable]
    for package in packages[request.param]:
        command.extend(["--with", package])

    def run(*args):
        try:
            subprocess.run(
                [*command, *args],
                check=True,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=180,
            )
        except subprocess.CalledProcessError as exc:
            pytest.fail(f"Wallet generation failed:\n{exc.stdout}\n{exc.stderr}")

    if request.param == "legacy":
        run(
            "python",
            "-c",
            "import sys; from bittensor_wallet import Wallet; "
            "w = Wallet(name=sys.argv[1], path=sys.argv[2], hotkey='default'); "
            "w.create_new_coldkey(use_password=False); "
            "w.create_new_hotkey(use_password=False)",
            name,
            str(path),
        )
    else:
        wallet_args = [
            "--wallet-name",
            name,
            "--hotkey",
            "default",
            "--wallet-path",
            str(path),
            "--n-words",
            "12",
        ]
        run("btcli", "wallet", "new-coldkey", *wallet_args, "--no-use-password")
        run("btcli", "wallet", "new-hotkey", *wallet_args)

    wallet_dir = path / name
    coldkey_data = json.loads((wallet_dir / "coldkeypub.txt").read_text())
    hotkey_data = json.loads((wallet_dir / "hotkeys/default").read_text())
    # Read addresses from the producer's JSON, not from the reader being tested.
    # Also ensure the legacy case genuinely exercises the old serialization.
    assert ("cryptoType" in hotkey_data) == (request.param != "legacy")
    return Wallet(name=name, path=str(path)), hotkey_data["ss58Address"], coldkey_data["ss58Address"]


@pytest_asyncio.fixture(scope="module")
async def wallet_compatibility_service(docker_network, localchain, generated_legacy_wallet, pylon_service_image, anvil):
    wallet, _, _ = generated_legacy_wallet
    netuid = await localchain.get_total_networks()
    await localchain.register_subnet(DevAccount.ALICE.wallet)
    await localchain.transfer(DevAccount.ALICE.wallet, wallet.coldkeypub.ss58_address, 10_000)
    await localchain.register_neuron(wallet, netuid)

    container = PylonServiceContainer(
        image=str(pylon_service_image),
        chain_url=localchain.internal_ws_url,
        wallets_path=wallet.path,
        startup_timeout=60,
    ).with_network(docker_network)
    container.with_envs(
        PYLON_IDENTITIES='["compatibility"]',
        PYLON_ID_COMPATIBILITY_WALLET_NAME=wallet.name,
        PYLON_ID_COMPATIBILITY_HOTKEY_NAME=wallet.hotkey_str,
        PYLON_ID_COMPATIBILITY_NETUID=str(netuid),
        PYLON_ID_COMPATIBILITY_TOKEN="compatibility_token",
    )
    with container:
        yield container


def test_legacy_wallet_can_read_and_sign(wallet_compatibility_service, generated_legacy_wallet):
    _, expected_hotkey, expected_coldkey = generated_legacy_wallet
    config = Config(
        address=wallet_compatibility_service.api_url,
        identity_name=IdentityName("compatibility"),
        identity_token=PylonAuthToken("compatibility_token"),
        timeout=PylonTimeout(read=120),
    )
    with PylonClient(config) as client:
        neurons = client.v1.identity.get_latest_neurons()
        assert neurons.neurons[expected_hotkey].coldkey == expected_coldkey
        commitment = CommitmentDataHex("0xdeadbeef")
        client.v1.identity.set_commitment(commitment)
        result = client.v1.identity.get_own_commitment()
        assert result.hotkey == expected_hotkey
        assert result.commitment == commitment
        assert result.block.number > 0
