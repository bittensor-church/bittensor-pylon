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

from pylon_service.bittensor.contact_router import BittensorContactRouter
from pylon_service.bittensor.exceptions import ArchiveFallbackException, RuntimeApiUnavailableException
from pylon_service.bittensor.mock_contact import MockBittensorContact


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
def contact_router(main_contact, archive_contact):
    return BittensorContactRouter(
        wallet=Wallet(),
        main_contact=main_contact,
        archive_contact=archive_contact,
        archive_blocks_cutoff=ArchiveBlocksCutoff(300),
    )


@pytest.mark.asyncio
async def test_contact_router_recent_block_uses_main_contact(
    contact_router, main_contact, archive_contact, test_neuron
):
    recent_block = Block(number=BlockNumber(450), hash=BlockHash("0xrecent"))
    latest_block = Block(number=BlockNumber(500), hash=BlockHash("0xlatest"))
    expected_neurons = [test_neuron]

    async with contact_router:
        async with main_contact.mock_behavior(
            get_latest_block=[latest_block],
            get_neurons_list=[expected_neurons],
        ):
            result = await contact_router.get_neurons_list(netuid=NetUid(1), block=recent_block)

    assert result == expected_neurons
    assert main_contact.calls["get_latest_block"] == [()]
    assert main_contact.calls["get_neurons_list"] == [(NetUid(1), recent_block)]
    assert archive_contact.calls["get_neurons_list"] == []


@pytest.mark.asyncio
async def test_contact_router_unknown_block_falls_back_to_archive(
    contact_router, main_contact, archive_contact, test_neuron
):
    recent_block = Block(number=BlockNumber(450), hash=BlockHash("0xrecent"))
    latest_block = Block(number=BlockNumber(500), hash=BlockHash("0xlatest"))
    expected_neurons = [test_neuron]

    async with contact_router:
        async with (
            main_contact.mock_behavior(
                get_latest_block=[latest_block],
                get_neurons_list=[UnknownBlock()],
            ),
            archive_contact.mock_behavior(
                get_neurons_list=[expected_neurons],
            ),
        ):
            result = await contact_router.get_neurons_list(netuid=NetUid(1), block=recent_block)

    assert result == expected_neurons
    assert main_contact.calls["get_neurons_list"] == [(NetUid(1), recent_block)]
    assert archive_contact.calls["get_neurons_list"] == [(NetUid(1), recent_block)]


@pytest.mark.asyncio
async def test_contact_router_unknown_block_on_both_nodes_raises_archive_fallback(
    contact_router, main_contact, archive_contact
):
    recent_block = Block(number=BlockNumber(450), hash=BlockHash("0xrecent"))
    latest_block = Block(number=BlockNumber(500), hash=BlockHash("0xlatest"))

    async with contact_router:
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
                await contact_router.get_neurons_list(netuid=NetUid(1), block=recent_block)


@pytest.mark.asyncio
async def test_contact_router_missing_runtime_method_on_stale_block_raises_runtime_api_unavailable(
    contact_router, main_contact, archive_contact
):
    """
    A 4003 'Exported method ... is not found' from the archive must surface as an honest
    RuntimeApiUnavailableException, not the misleading 'block data is unavailable' message.
    """
    stale_block = Block(number=BlockNumber(100), hash=BlockHash("0xstale"))
    latest_block = Block(number=BlockNumber(500), hash=BlockHash("0xlatest"))

    async with contact_router:
        async with (
            main_contact.mock_behavior(get_latest_block=[latest_block]),
            archive_contact.mock_behavior(
                get_alpha_prices=[
                    UnknownBlock(
                        "Client error: Execution failed: Other: Exported method SwapRuntimeApi_current_alpha_price_all is not found"
                    )
                ]
            ),
        ):
            with pytest.raises(RuntimeApiUnavailableException, match="not available at block 100"):
                await contact_router.get_alpha_prices(stale_block)


@pytest.mark.asyncio
async def test_contact_router_genuine_unknown_block_on_stale_block_raises_archive_fallback(
    contact_router, main_contact, archive_contact
):
    """
    A genuine unknown/pruned block (no 'Exported method' signature) keeps the archive-unavailable message.
    """
    stale_block = Block(number=BlockNumber(100), hash=BlockHash("0xstale"))
    latest_block = Block(number=BlockNumber(500), hash=BlockHash("0xlatest"))

    async with contact_router:
        async with (
            main_contact.mock_behavior(get_latest_block=[latest_block]),
            archive_contact.mock_behavior(
                get_alpha_prices=[UnknownBlock("Api called for an unknown Block: State already discarded")]
            ),
        ):
            with pytest.raises(ArchiveFallbackException, match="unavailable on the archive node"):
                await contact_router.get_alpha_prices(stale_block)
