import pytest
from pydantic import ValidationError

from pylon_commons.settings import Settings


@pytest.fixture(autouse=True)
def clean_network_env(monkeypatch: pytest.MonkeyPatch):
    for var in (
        "PYLON_BITTENSOR_NETWORK",
        "PYLON_BITTENSOR_ARCHIVE_NETWORK",
        "PYLON_EVM_RPC_URL",
        "PYLON_EVM_ARCHIVE_RPC_URL",
    ):
        monkeypatch.delenv(var, raising=False)


def make_settings(**overrides: str) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore


def test_defaults_keep_default_networks():
    settings = make_settings()

    assert (settings.bittensor_network, settings.bittensor_archive_network) == ("finney", "archive")


def test_both_bittensor_networks_overridden_together_pass():
    settings = make_settings(
        bittensor_network="ws://localhost:9944",
        bittensor_archive_network="ws://archive:9944",
    )

    assert (settings.bittensor_network, settings.bittensor_archive_network) == (
        "ws://localhost:9944",
        "ws://archive:9944",
    )


def test_repeating_default_explicitly_passes():
    settings = make_settings(
        bittensor_network="finney",
        bittensor_archive_network="archive",
    )

    assert (settings.bittensor_network, settings.bittensor_archive_network) == ("finney", "archive")


def test_both_evm_urls_overridden_together_pass():
    settings = make_settings(
        evm_rpc_url="http://main:8545",
        evm_archive_rpc_url="http://archive:8545",
    )

    assert (settings.evm_rpc_url, settings.evm_archive_rpc_url) == ("http://main:8545", "http://archive:8545")


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"bittensor_network": "ws://localhost:9944"}, id="only_bittensor_main"),
        pytest.param({"bittensor_archive_network": "ws://archive:9944"}, id="only_bittensor_archive"),
        pytest.param({"evm_rpc_url": "http://main:8545"}, id="only_evm_main"),
        pytest.param({"evm_archive_rpc_url": "http://archive:8545"}, id="only_evm_archive"),
    ],
)
def test_overriding_only_one_network_of_a_pair_raises(overrides: dict[str, str]):
    with pytest.raises(ValidationError):
        make_settings(**overrides)
