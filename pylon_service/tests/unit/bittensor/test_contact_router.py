import ipaddress

import pytest
from bittensor_wallet import Wallet
from pylon_commons.currency import Currency, CurrencyRao, Token
from pylon_commons.models import AxonInfo, AxonProtocol, Block, Neuron, Stakes, SubnetPrice, SubnetPrices
from pylon_commons.types import (
    AlphaPriceRao,
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
from pylon_service.bittensor.exceptions import ArchiveFallbackException
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
async def test_contact_router_get_alpha_prices_uses_main_for_recent_block(
    contact_router, main_contact, archive_contact
):
    """
    A recent block reads alpha prices from the main contact, not the archive.
    """
    recent_block = Block(number=BlockNumber(450), hash=BlockHash("0xrecent"))
    latest_block = Block(number=BlockNumber(500), hash=BlockHash("0xlatest"))
    expected = SubnetPrices(
        block=recent_block,
        prices={
            NetUid(1): AlphaPriceRao(CurrencyRao[Token.TAO](5)),
            NetUid(2): AlphaPriceRao(CurrencyRao[Token.TAO](7)),
        },
    )

    async with contact_router:
        async with main_contact.mock_behavior(get_latest_block=[latest_block], get_alpha_prices=[expected]):
            result = await contact_router.get_alpha_prices(recent_block)

    assert result == expected
    assert main_contact.calls["get_alpha_prices"] == [(recent_block,)]
    assert archive_contact.calls["get_alpha_prices"] == []


@pytest.mark.asyncio
async def test_contact_router_get_alpha_price_falls_back_to_archive_for_stale_block(
    contact_router, main_contact, archive_contact
):
    """
    A stale block (older than the 300-block cutoff) routes the single-subnet price read to the archive contact.
    """
    latest_block = Block(number=BlockNumber(100_000), hash=BlockHash("0xlatest"))
    stale_block = Block(number=BlockNumber(1), hash=BlockHash("0xstale"))
    expected = SubnetPrice(block=stale_block, netuid=NetUid(1), price=AlphaPriceRao(CurrencyRao[Token.TAO](42)))

    async with contact_router:
        async with main_contact.mock_behavior(get_latest_block=[latest_block]):
            async with archive_contact.mock_behavior(get_alpha_price=[expected]):
                result = await contact_router.get_alpha_price(NetUid(1), stale_block)

    assert result == expected
    assert archive_contact.calls["get_alpha_price"] == [(NetUid(1), stale_block)]
