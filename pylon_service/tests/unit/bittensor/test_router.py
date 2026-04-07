import ipaddress

import pytest
from bittensor_wallet import Wallet
from pylon_commons.currency import Currency, Token
from pylon_commons.models import AxonInfo, AxonProtocol, Block, Neuron, Stakes
from pylon_commons.types import (
    AlphaStake,
    ArchiveBlocksCutoff,
    BlockHash,
    BlockNumber,
    Coldkey,
    Consensus,
    Dividends,
    Emission,
    Hotkey,
    Incentive,
    NetUid,
    NeuronActive,
    NeuronUid,
    Port,
    PruningScore,
    Rank,
    Stake,
    TaoStake,
    Timestamp,
    TotalStake,
    Trust,
    ValidatorPermit,
    ValidatorTrust,
)
from turbobt.substrate.exceptions import UnknownBlock

from pylon_service.bittensor.contact import MockBittensorContact
from pylon_service.bittensor.exceptions import ArchiveFallbackException
from pylon_service.bittensor.router import BittensorRouter


@pytest.fixture
def test_neuron():
    return Neuron(
        uid=NeuronUid(1),
        coldkey=Coldkey("coldkey_1"),
        hotkey=Hotkey("test_hotkey"),
        active=NeuronActive(True),
        axon_info=AxonInfo(ip=ipaddress.IPv4Address("192.168.1.1"), port=Port(8080), protocol=AxonProtocol.TCP),
        stake=Stake(100.0),
        rank=Rank(0.5),
        emission=Emission(Currency[Token.ALPHA](10.0)),
        incentive=Incentive(0.8),
        consensus=Consensus(0.9),
        trust=Trust(0.7),
        validator_trust=ValidatorTrust(0.6),
        dividends=Dividends(0.4),
        last_update=Timestamp(1000),
        validator_permit=ValidatorPermit(True),
        pruning_score=PruningScore(50),
        stakes=Stakes(
            alpha=AlphaStake(Currency[Token.ALPHA](75.0)),
            tao=TaoStake(Currency[Token.TAO](25.0)),
            total=TotalStake(Currency[Token.ALPHA](100.0)),
        ),
    )


@pytest.fixture
def main_contact():
    return MockBittensorContact(wallet=Wallet())


@pytest.fixture
def archive_contact():
    return MockBittensorContact(wallet=Wallet())


@pytest.fixture
def router(main_contact, archive_contact):
    return BittensorRouter(
        wallet=Wallet(),
        main_contact=main_contact,
        archive_contact=archive_contact,
        archive_blocks_cutoff=ArchiveBlocksCutoff(300),
    )


@pytest.mark.asyncio
async def test_router_recent_block_uses_main_contact(router, main_contact, archive_contact, test_neuron):
    recent_block = Block(number=BlockNumber(450), hash=BlockHash("0xrecent"))
    latest_block = Block(number=BlockNumber(500), hash=BlockHash("0xlatest"))
    expected_neurons = [test_neuron]

    async with router:
        async with main_contact.mock_behavior(
            get_latest_block=[latest_block],
            get_neurons_list=[expected_neurons],
        ):
            result = await router.get_neurons_list(netuid=NetUid(1), block=recent_block)

    assert result == expected_neurons
    assert main_contact.calls["get_latest_block"] == [()]
    assert main_contact.calls["get_neurons_list"] == [(NetUid(1), recent_block)]
    assert archive_contact.calls["get_neurons_list"] == []


@pytest.mark.asyncio
async def test_router_unknown_block_falls_back_to_archive(router, main_contact, archive_contact, test_neuron):
    recent_block = Block(number=BlockNumber(450), hash=BlockHash("0xrecent"))
    latest_block = Block(number=BlockNumber(500), hash=BlockHash("0xlatest"))
    expected_neurons = [test_neuron]

    async with router:
        async with (
            main_contact.mock_behavior(
                get_latest_block=[latest_block],
                get_neurons_list=[UnknownBlock()],
            ),
            archive_contact.mock_behavior(
                get_neurons_list=[expected_neurons],
            ),
        ):
            result = await router.get_neurons_list(netuid=NetUid(1), block=recent_block)

    assert result == expected_neurons
    assert main_contact.calls["get_neurons_list"] == [(NetUid(1), recent_block)]
    assert archive_contact.calls["get_neurons_list"] == [(NetUid(1), recent_block)]


@pytest.mark.asyncio
async def test_router_unknown_block_on_both_nodes_raises_archive_fallback(router, main_contact, archive_contact):
    recent_block = Block(number=BlockNumber(450), hash=BlockHash("0xrecent"))
    latest_block = Block(number=BlockNumber(500), hash=BlockHash("0xlatest"))

    async with router:
        async with (
            main_contact.mock_behavior(
                get_latest_block=[latest_block],
                get_neurons_list=[UnknownBlock()],
            ),
            archive_contact.mock_behavior(
                get_neurons_list=[UnknownBlock()],
            ),
        ):
            with pytest.raises(ArchiveFallbackException, match="unavailable on both main and archive nodes"):
                await router.get_neurons_list(netuid=NetUid(1), block=recent_block)
