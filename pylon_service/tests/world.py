from __future__ import annotations

from dataclasses import dataclass

from bittensor_wallet import Wallet
from pylon_commons.models import Block, Neuron
from pylon_commons.types import BlockHash, BlockNumber, Hotkey, HotkeyName, IdentityName, NetUid, NeuronUid, PylonAuthToken, WalletName

from pylon_service.identities import Identity
from tests.factories import NeuronFactory
from tests.mock_bittensor_client import MockBittensorClient


@dataclass(frozen=True)
class SharedWorld:
    open_access_main: MockBittensorClient
    open_access_archive: MockBittensorClient
    sn1_main: MockBittensorClient
    sn1_archive: MockBittensorClient
    sn2_main: MockBittensorClient
    sn2_archive: MockBittensorClient
    identities: dict[IdentityName, Identity]
    default_latest_block: Block
    default_neurons: dict[NetUid, list[Neuron]]

    @property
    def contacts(self) -> tuple[MockBittensorClient, ...]:
        return (
            self.open_access_main,
            self.open_access_archive,
            self.sn1_main,
            self.sn1_archive,
            self.sn2_main,
            self.sn2_archive,
        )

    def reset(self) -> None:
        for contact in self.contacts:
            contact.reset()

    def seed_defaults(self) -> None:
        for contact in self.contacts:
            contact.set_default("get_latest_block", self.default_latest_block)
            contact.set_default("get_neurons_list", lambda netuid, block, neurons=self.default_neurons: neurons[netuid])


def build_test_identities() -> dict[IdentityName, Identity]:
    return {
        IdentityName("sn1"): Identity(
            identity_name=IdentityName("sn1"),
            wallet_name=WalletName("wallet_sn1"),
            hotkey_name=HotkeyName("hotkey_sn1"),
            netuid=NetUid(1),
            token=PylonAuthToken("token_sn1"),
        ),
        IdentityName("sn2"): Identity(
            identity_name=IdentityName("sn2"),
            wallet_name=WalletName("wallet_sn2"),
            hotkey_name=HotkeyName("hotkey_sn2"),
            netuid=NetUid(2),
            token=PylonAuthToken("token_sn2"),
        ),
    }


def default_latest_block() -> Block:
    return Block(number=BlockNumber(1000), hash=BlockHash("0xshared-latest-block"))


def default_neurons() -> dict[NetUid, list[Neuron]]:
    def build_neuron(netuid: int, uid: int, hotkey: str) -> Neuron:
        return NeuronFactory.build(
            uid=NeuronUid(uid),
            hotkey=Hotkey(hotkey),
        )

    return {
        NetUid(1): [
            build_neuron(1, 1, "hotkey1"),
            build_neuron(1, 2, "hotkey2"),
            build_neuron(1, 3, "hotkey3"),
        ],
        NetUid(2): [
            build_neuron(2, 1, "hotkey1"),
            build_neuron(2, 2, "hotkey2"),
            build_neuron(2, 3, "hotkey3"),
        ],
    }
