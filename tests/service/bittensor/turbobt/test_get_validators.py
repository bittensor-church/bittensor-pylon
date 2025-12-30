import ipaddress
from unittest.mock import Mock

import pytest
from turbobt.neuron import AxonInfo as TurboBtAxonInfo
from turbobt.neuron import AxonProtocolEnum as TurboBtAxonProtocolEnum
from turbobt.neuron import Neuron as TurboBtNeuron

from pylon_client._internal.common.currency import Currency, Token
from pylon_client._internal.common.models import (
    AxonInfo,
    AxonProtocol,
    Block,
    Neuron,
    Stakes,
    SubnetValidators,
)
from pylon_client._internal.common.types import (
    AlphaStake,
    BlockHash,
    BlockNumber,
    Coldkey,
    Consensus,
    Dividends,
    Emission,
    Hotkey,
    Incentive,
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


@pytest.fixture
def subnet_spec(subnet_spec):
    subnet_spec.list_neurons.return_value = [
        TurboBtNeuron(
            subnet=subnet_spec,
            uid=1,
            coldkey="coldkey1",
            hotkey="hotkey1",
            active=True,
            axon_info=TurboBtAxonInfo(
                ip=ipaddress.IPv4Address("192.168.1.1"),
                port=8080,
                protocol=TurboBtAxonProtocolEnum.TCP,
            ),
            prometheus_info=Mock(),
            stake=100.0,
            rank=0.5,
            emission=10.0,
            incentive=0.8,
            consensus=0.9,
            trust=0.7,
            validator_trust=0.6,
            dividends=0.4,
            last_update=1000,
            validator_permit=True,
            pruning_score=50,
        ),
        TurboBtNeuron(
            subnet=subnet_spec,
            uid=2,
            coldkey="coldkey2",
            hotkey="hotkey2",
            active=False,
            axon_info=TurboBtAxonInfo(
                ip=ipaddress.IPv4Address("192.168.1.2"),
                port=8081,
                protocol=TurboBtAxonProtocolEnum.UDP,
            ),
            prometheus_info=Mock(),
            stake=200.0,
            rank=0.6,
            emission=20.0,
            incentive=0.7,
            consensus=0.8,
            trust=0.9,
            validator_trust=0.5,
            dividends=0.3,
            last_update=2000,
            validator_permit=False,
            pruning_score=60,
        ),
        TurboBtNeuron(
            subnet=subnet_spec,
            uid=3,
            coldkey="coldkey3",
            hotkey="hotkey3",
            active=True,
            axon_info=TurboBtAxonInfo(
                ip=ipaddress.IPv4Address("192.168.1.3"),
                port=8082,
                protocol=TurboBtAxonProtocolEnum.TCP,
            ),
            prometheus_info=Mock(),
            stake=300.0,
            rank=0.7,
            emission=30.0,
            incentive=0.9,
            consensus=0.95,
            trust=0.85,
            validator_trust=0.75,
            dividends=0.5,
            last_update=3000,
            validator_permit=True,
            pruning_score=70,
        ),
    ]
    subnet_spec.get_state.return_value = {
        "netuid": 1,
        "hotkeys": ["hotkey1", "hotkey2", "hotkey3"],
        "coldkeys": ["coldkey1", "coldkey2", "coldkey3"],
        "active": [True, False, True],
        "validator_permit": [True, False, True],
        "pruning_score": [50, 60, 70],
        "last_update": [1000, 2000, 3000],
        "emission": [10_000_000_000, 20_000_000_000, 30_000_000_000],
        "dividends": [400_000_000, 300_000_000, 500_000_000],
        "incentives": [800_000_000, 700_000_000, 900_000_000],
        "consensus": [900_000_000, 800_000_000, 950_000_000],
        "trust": [700_000_000, 900_000_000, 850_000_000],
        "rank": [500_000_000, 600_000_000, 700_000_000],
        "block_at_registration": [0, 0, 0],
        "alpha_stake": [50_000_000_000, 100_000_000_000, 150_000_000_000],
        "tao_stake": [30_000_000_000, 60_000_000_000, 90_000_000_000],
        "total_stake": [55_400_000_000, 110_800_000_000, 166_200_000_000],
        "emission_history": [[], [], []],
    }
    return subnet_spec


@pytest.fixture
def block():
    return Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))


@pytest.fixture
def validators(block):
    return SubnetValidators(
        block=block,
        validators=[
            Neuron(
                uid=NeuronUid(3),
                coldkey=Coldkey("coldkey3"),
                hotkey=Hotkey("hotkey3"),
                active=NeuronActive(True),
                axon_info=AxonInfo(ip=ipaddress.IPv4Address("192.168.1.3"), port=Port(8082), protocol=AxonProtocol.TCP),
                stake=Stake(300.0),
                rank=Rank(0.7),
                emission=Emission(Currency[Token.ALPHA](30.0)),
                incentive=Incentive(0.9),
                consensus=Consensus(0.95),
                trust=Trust(0.85),
                validator_trust=ValidatorTrust(0.75),
                dividends=Dividends(0.5),
                last_update=Timestamp(3000),
                validator_permit=ValidatorPermit(True),
                pruning_score=PruningScore(70),
                stakes=Stakes(
                    alpha=AlphaStake(Currency[Token.ALPHA](150.0)),
                    tao=TaoStake(Currency[Token.TAO](90.0)),
                    total=TotalStake(Currency[Token.ALPHA](166.2)),
                ),
            ),
            Neuron(
                uid=NeuronUid(1),
                coldkey=Coldkey("coldkey1"),
                hotkey=Hotkey("hotkey1"),
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
                    alpha=AlphaStake(Currency[Token.ALPHA](50.0)),
                    tao=TaoStake(Currency[Token.TAO](30.0)),
                    total=TotalStake(Currency[Token.ALPHA](55.4)),
                ),
            ),
        ],
    )


@pytest.mark.asyncio
async def test_turbobt_client_get_validators(turbobt_client, block, validators):
    result = await turbobt_client.get_validators(netuid=1, block=block)
    assert result == validators
