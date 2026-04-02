"""
Tests for the GET /subnet/{netuid}/block/{block_number}/neurons endpoint.
"""

from ipaddress import IPv4Address

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient
from pylon_commons.currency import Currency, Token
from pylon_commons.models import AxonInfo, AxonProtocol, Block, Neuron, Stakes, SubnetNeurons
from pylon_commons.types import (
    AlphaStake,
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
from turbobt.block import Block as TurboBtBlock
from turbobt.neuron import Neuron as TurboBtNeuron

from pylon_service.bittensor.client import MockTurboBTtransport

TEST_NETUID = NetUid(1)


def _build_neuron(
    *,
    uid: int,
    coldkey: str,
    hotkey: str,
    active: bool,
    ip: str,
    port: int,
    protocol: AxonProtocol,
    stake: float,
    rank: float,
    emission: float,
    incentive: float,
    consensus: float,
    trust: float,
    validator_trust: float,
    dividends: float,
    last_update: int,
    validator_permit: bool,
    pruning_score: int,
    alpha_stake: float,
    tao_stake: float,
    total_stake: float,
) -> Neuron:
    return Neuron(
        uid=NeuronUid(uid),
        coldkey=Coldkey(coldkey),
        hotkey=Hotkey(hotkey),
        active=NeuronActive(active),
        axon_info=AxonInfo(ip=IPv4Address(ip), port=Port(port), protocol=protocol),
        stake=Stake(stake),
        rank=Rank(rank),
        emission=Emission(Currency[Token.ALPHA](emission)),
        incentive=Incentive(incentive),
        consensus=Consensus(consensus),
        trust=Trust(trust),
        validator_trust=ValidatorTrust(validator_trust),
        dividends=Dividends(dividends),
        last_update=Timestamp(last_update),
        validator_permit=ValidatorPermit(validator_permit),
        pruning_score=PruningScore(pruning_score),
        stakes=Stakes(
            alpha=AlphaStake(Currency[Token.ALPHA](alpha_stake)),
            tao=TaoStake(Currency[Token.TAO](tao_stake)),
            total=TotalStake(Currency[Token.ALPHA](total_stake)),
        ),
    )


@pytest.fixture
def block() -> Block:
    return Block(number=BlockNumber(123), hash=BlockHash("0xabc123"))


@pytest.fixture
def raw_block(block: Block, turbobt_block_builder) -> TurboBtBlock:
    return turbobt_block_builder(int(block.number), str(block.hash))


@pytest.fixture
def subnet_neurons(block: Block) -> SubnetNeurons:
    neuron_a = _build_neuron(
        uid=10,
        coldkey="coldkey-a",
        hotkey="hotkey-a",
        active=True,
        ip="192.168.1.10",
        port=8080,
        protocol=AxonProtocol.HTTP,
        stake=1.5,
        rank=0.11,
        emission=2.5,
        incentive=0.22,
        consensus=0.33,
        trust=0.44,
        validator_trust=0.55,
        dividends=0.66,
        last_update=111,
        validator_permit=True,
        pruning_score=7,
        alpha_stake=3.5,
        tao_stake=4.5,
        total_stake=8.0,
    )
    neuron_b = _build_neuron(
        uid=11,
        coldkey="coldkey-b",
        hotkey="hotkey-b",
        active=False,
        ip="10.0.0.2",
        port=9090,
        protocol=AxonProtocol.TCP,
        stake=9.5,
        rank=0.77,
        emission=1.25,
        incentive=0.88,
        consensus=0.99,
        trust=0.12,
        validator_trust=0.34,
        dividends=0.56,
        last_update=222,
        validator_permit=False,
        pruning_score=8,
        alpha_stake=5.5,
        tao_stake=6.5,
        total_stake=12.0,
    )
    return SubnetNeurons(block=block, neurons={neuron_a.hotkey: neuron_a, neuron_b.hotkey: neuron_b})


@pytest.fixture
def raw_neurons(subnet_neurons: SubnetNeurons, turbobt_neuron_builder) -> list[TurboBtNeuron]:
    return [turbobt_neuron_builder(neuron) for neuron in subnet_neurons.neurons.values()]


@pytest.fixture
def raw_subnet_state(subnet_neurons: SubnetNeurons, raw_subnet_state_builder) -> dict[str, object]:
    return raw_subnet_state_builder(TEST_NETUID, subnet_neurons)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_block_number",
    [
        pytest.param("not_a_number", id="string_value"),
        pytest.param("123.456", id="float_string"),
        pytest.param("true", id="boolean_string"),
    ],
)
async def test_get_neurons_open_access_invalid_block_number_type(
    test_client: AsyncTestClient, invalid_block_number: str
):
    response = await test_client.get(f"/api/v1/subnet/{int(TEST_NETUID)}/block/{invalid_block_number}/neurons")

    assert response.status_code == HTTP_404_NOT_FOUND, response.content
    assert response.json() == {
        "status_code": HTTP_404_NOT_FOUND,
        "detail": "Not Found",
    }


@pytest.mark.asyncio
async def test_get_neurons_open_access_success(
    test_client: AsyncTestClient,
    mock_turbobt_transport: MockTurboBTtransport,
    block: Block,
    raw_block: TurboBtBlock,
    subnet_neurons: SubnetNeurons,
    raw_neurons: list[TurboBtNeuron],
    raw_subnet_state: dict[str, object],
):
    mock_turbobt_transport.set_latest_block(raw_block)
    mock_turbobt_transport.add_block(raw_block)
    mock_turbobt_transport.add_neurons_range(TEST_NETUID, int(block.number), int(block.number), raw_neurons)
    mock_turbobt_transport.add_subnet_state_range(TEST_NETUID, int(block.number), int(block.number), raw_subnet_state)

    response = await test_client.get(f"/api/v1/subnet/{int(TEST_NETUID)}/block/{block.number}/neurons")

    assert response.status_code == HTTP_200_OK, response.content
    assert response.json() == {
        "block": {"number": 123, "hash": "0xabc123"},
        "neurons": {
            "hotkey-a": {
                "uid": 10,
                "coldkey": "coldkey-a",
                "hotkey": "hotkey-a",
                "active": True,
                "axon_info": {"ip": "192.168.1.10", "port": 8080, "protocol": 4},
                "stake": 1.5,
                "rank": 0.11,
                "emission": 2.5,
                "incentive": 0.22,
                "consensus": 0.33,
                "trust": 0.44,
                "validator_trust": 0.55,
                "dividends": 0.66,
                "last_update": 111,
                "validator_permit": True,
                "pruning_score": 7,
                "stakes": {"alpha": 3.5, "tao": 4.5, "total": 8.0},
            },
            "hotkey-b": {
                "uid": 11,
                "coldkey": "coldkey-b",
                "hotkey": "hotkey-b",
                "active": False,
                "axon_info": {"ip": "10.0.0.2", "port": 9090, "protocol": 0},
                "stake": 9.5,
                "rank": 0.77,
                "emission": 1.25,
                "incentive": 0.88,
                "consensus": 0.99,
                "trust": 0.12,
                "validator_trust": 0.34,
                "dividends": 0.56,
                "last_update": 222,
                "validator_permit": False,
                "pruning_score": 8,
                "stakes": {"alpha": 5.5, "tao": 6.5, "total": 12.0},
            },
        },
    }

    assert mock_turbobt_transport.calls["get_block"] == [(block.number,), (BlockNumber(-1),)]
    assert mock_turbobt_transport.calls["list_neurons"] == [(TEST_NETUID, block.hash)]
    assert mock_turbobt_transport.calls["get_subnet_state"] == [(TEST_NETUID, block.hash)]


@pytest.mark.asyncio
async def test_get_latest_neurons_open_access_success(
    test_client: AsyncTestClient,
    mock_turbobt_transport: MockTurboBTtransport,
    block: Block,
    raw_block: TurboBtBlock,
    subnet_neurons: SubnetNeurons,
    raw_neurons: list[TurboBtNeuron],
    raw_subnet_state: dict[str, object],
):
    mock_turbobt_transport.set_latest_block(raw_block)
    mock_turbobt_transport.add_block(raw_block)
    mock_turbobt_transport.add_neurons_range(TEST_NETUID, int(block.number), None, raw_neurons)
    mock_turbobt_transport.add_subnet_state_range(TEST_NETUID, int(block.number), None, raw_subnet_state)

    response = await test_client.get(f"/api/v1/subnet/{int(TEST_NETUID)}/block/latest/neurons")

    assert response.status_code == HTTP_200_OK, response.content
    assert response.json() == {
        "block": {"number": 123, "hash": "0xabc123"},
        "neurons": {
            "hotkey-a": {
                "uid": 10,
                "coldkey": "coldkey-a",
                "hotkey": "hotkey-a",
                "active": True,
                "axon_info": {"ip": "192.168.1.10", "port": 8080, "protocol": 4},
                "stake": 1.5,
                "rank": 0.11,
                "emission": 2.5,
                "incentive": 0.22,
                "consensus": 0.33,
                "trust": 0.44,
                "validator_trust": 0.55,
                "dividends": 0.66,
                "last_update": 111,
                "validator_permit": True,
                "pruning_score": 7,
                "stakes": {"alpha": 3.5, "tao": 4.5, "total": 8.0},
            },
            "hotkey-b": {
                "uid": 11,
                "coldkey": "coldkey-b",
                "hotkey": "hotkey-b",
                "active": False,
                "axon_info": {"ip": "10.0.0.2", "port": 9090, "protocol": 0},
                "stake": 9.5,
                "rank": 0.77,
                "emission": 1.25,
                "incentive": 0.88,
                "consensus": 0.99,
                "trust": 0.12,
                "validator_trust": 0.34,
                "dividends": 0.56,
                "last_update": 222,
                "validator_permit": False,
                "pruning_score": 8,
                "stakes": {"alpha": 5.5, "tao": 6.5, "total": 12.0},
            },
        },
    }

    assert mock_turbobt_transport.calls["get_block"] == [(BlockNumber(-1),), (BlockNumber(-1),)]
    assert mock_turbobt_transport.calls["list_neurons"] == [(TEST_NETUID, block.hash)]
    assert mock_turbobt_transport.calls["get_subnet_state"] == [(TEST_NETUID, block.hash)]


@pytest.mark.asyncio
async def test_get_neurons_open_access_block_not_found(
    test_client: AsyncTestClient, mock_turbobt_transport: MockTurboBTtransport
):
    response = await test_client.get(f"/api/v1/subnet/{int(TEST_NETUID)}/block/123/neurons")

    assert response.status_code == HTTP_404_NOT_FOUND, response.content
    assert response.json() == {
        "status_code": HTTP_404_NOT_FOUND,
        "detail": "Block 123 not found.",
    }

    assert mock_turbobt_transport.calls["get_block"] == [(BlockNumber(123),)]
