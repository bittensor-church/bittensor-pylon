"""
Tests for the GET /subnet/{netuid}/block/{block_number}/validators endpoint.
"""

from collections.abc import AsyncIterator
from ipaddress import IPv4Address
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

import pytest
import pytest_asyncio
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient
from pylon_commons.currency import Currency, Token
from pylon_commons.models import AxonInfo, AxonProtocol, Block, Neuron, Stakes, SubnetValidators
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


def _build_neuron(
    *,
    uid: int,
    coldkey: str,
    hotkey: str,
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
    pruning_score: int,
    alpha_stake: float,
    tao_stake: float,
    total_stake: float,
) -> Neuron:
    return Neuron(
        uid=NeuronUid(uid),
        coldkey=Coldkey(coldkey),
        hotkey=Hotkey(hotkey),
        active=NeuronActive(True),
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
        validator_permit=ValidatorPermit(True),
        pruning_score=PruningScore(pruning_score),
        stakes=Stakes(
            alpha=AlphaStake(Currency[Token.ALPHA](alpha_stake)),
            tao=TaoStake(Currency[Token.TAO](tao_stake)),
            total=TotalStake(Currency[Token.ALPHA](total_stake)),
        ),
    )


def _build_turbobt_block(number: int, block_hash: str) -> TurboBtBlock:
    return TurboBtBlock(block_hash, number, client=None)


def _build_turbobt_neuron(neuron: Neuron) -> TurboBtNeuron:
    return cast(
        TurboBtNeuron,
        SimpleNamespace(
            uid=neuron.uid,
            coldkey=neuron.coldkey,
            hotkey=neuron.hotkey,
            active=neuron.active,
            axon_info=SimpleNamespace(
                ip=neuron.axon_info.ip,
                port=neuron.axon_info.port,
                protocol=neuron.axon_info.protocol,
            ),
            stake=neuron.stake,
            rank=neuron.rank,
            emission=neuron.emission,
            incentive=neuron.incentive,
            consensus=neuron.consensus,
            trust=neuron.trust,
            validator_trust=neuron.validator_trust,
            dividends=neuron.dividends,
            last_update=neuron.last_update,
            validator_permit=neuron.validator_permit,
            pruning_score=neuron.pruning_score,
        ),
    )


def _build_raw_subnet_state(netuid: NetUid, subnet_validators: SubnetValidators) -> dict[str, object]:
    validators = subnet_validators.validators
    return {
        "netuid": netuid,
        "hotkeys": [validator.hotkey for validator in validators],
        "coldkeys": [validator.coldkey for validator in validators],
        "active": [validator.active for validator in validators],
        "validator_permit": [validator.validator_permit for validator in validators],
        "pruning_score": [validator.pruning_score for validator in validators],
        "last_update": [validator.last_update for validator in validators],
        "emission": [Currency[Token.ALPHA](validator.emission).as_rao() for validator in validators],
        "dividends": [validator.dividends for validator in validators],
        "incentives": [validator.incentive for validator in validators],
        "consensus": [validator.consensus for validator in validators],
        "trust": [validator.trust for validator in validators],
        "rank": [validator.rank for validator in validators],
        "block_at_registration": [BlockNumber(0) for _ in validators],
        "alpha_stake": [Currency[Token.ALPHA](validator.stakes.alpha).as_rao() for validator in validators],
        "tao_stake": [Currency[Token.TAO](validator.stakes.tao).as_rao() for validator in validators],
        "total_stake": [Currency[Token.ALPHA](validator.stakes.total).as_rao() for validator in validators],
        "emission_history": [[Currency[Token.ALPHA](validator.emission).as_rao()] for validator in validators],
    }


@pytest.fixture
def mock_turbobt_transport() -> MockTurboBTtransport:
    return MockTurboBTtransport()


@pytest_asyncio.fixture
async def patched_test_client(
    test_client: AsyncTestClient, mock_turbobt_transport: MockTurboBTtransport
) -> AsyncIterator[AsyncTestClient]:
    with patch(
        "pylon_service.bittensor.client.get_turbobt_transport",
        return_value=mock_turbobt_transport,
    ):
        yield test_client


@pytest.fixture
def block() -> Block:
    return Block(number=BlockNumber(123), hash=BlockHash("0xabc123"))


@pytest.fixture
def raw_block(block: Block) -> TurboBtBlock:
    return _build_turbobt_block(int(block.number), str(block.hash))


@pytest.fixture
def subnet_validators(block: Block) -> SubnetValidators:
    return SubnetValidators(
        block=block,
        validators=[
            _build_neuron(
                uid=10,
                coldkey="coldkey-a",
                hotkey="hotkey-a",
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
                pruning_score=7,
                alpha_stake=3.5,
                tao_stake=4.5,
                total_stake=8.0,
            ),
            _build_neuron(
                uid=11,
                coldkey="coldkey-b",
                hotkey="hotkey-b",
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
                pruning_score=8,
                alpha_stake=5.5,
                tao_stake=6.5,
                total_stake=12.0,
            ),
        ],
    )


@pytest.fixture
def raw_validators(subnet_validators: SubnetValidators) -> list[TurboBtNeuron]:
    return [_build_turbobt_neuron(validator) for validator in subnet_validators.validators]


@pytest.fixture
def raw_subnet_state(subnet_validators: SubnetValidators) -> dict[str, object]:
    return _build_raw_subnet_state(NetUid(1), subnet_validators)


@pytest.mark.asyncio
async def test_get_validators_open_access_success(
    patched_test_client: AsyncTestClient,
    mock_turbobt_transport: MockTurboBTtransport,
    block: Block,
    raw_block: TurboBtBlock,
    raw_validators: list[TurboBtNeuron],
    raw_subnet_state: dict[str, object],
):
    mock_turbobt_transport.set_latest_block(raw_block)
    mock_turbobt_transport.add_block(raw_block)
    mock_turbobt_transport.add_neurons_range(NetUid(1), int(block.number), int(block.number), raw_validators)
    mock_turbobt_transport.add_subnet_state_range(NetUid(1), int(block.number), int(block.number), raw_subnet_state)

    response = await patched_test_client.get(f"/api/v1/subnet/1/block/{block.number}/validators")

    assert response.status_code == HTTP_200_OK
    assert response.json() == {
            "block": {"number": 123, "hash": "0xabc123"},
            "validators": [
                {
                    "uid": 11,
                    "coldkey": "coldkey-b",
                    "hotkey": "hotkey-b",
                    "active": True,
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
                    "validator_permit": True,
                    "pruning_score": 8,
                    "stakes": {"alpha": 5.5, "tao": 6.5, "total": 12.0},
                },
                {
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
            ],
        }

    assert mock_turbobt_transport.calls["get_block"] == [(block.number,), (BlockNumber(-1),)]
    assert mock_turbobt_transport.calls["list_neurons"] == [(NetUid(1), block.hash)]
    assert mock_turbobt_transport.calls["get_subnet_state"] == [(NetUid(1), block.hash)]


@pytest.mark.asyncio
async def test_get_latest_validators_open_access_success(
    patched_test_client: AsyncTestClient,
    mock_turbobt_transport: MockTurboBTtransport,
    block: Block,
    raw_block: TurboBtBlock,
    raw_validators: list[TurboBtNeuron],
    raw_subnet_state: dict[str, object],
):
    mock_turbobt_transport.set_latest_block(raw_block)
    mock_turbobt_transport.add_block(raw_block)
    mock_turbobt_transport.add_neurons_range(NetUid(1), int(block.number), None, raw_validators)
    mock_turbobt_transport.add_subnet_state_range(NetUid(1), int(block.number), None, raw_subnet_state)

    response = await patched_test_client.get("/api/v1/subnet/1/block/latest/validators")

    assert response.status_code == HTTP_200_OK
    assert response.json() == {
            "block": {"number": 123, "hash": "0xabc123"},
            "validators": [
                {
                    "uid": 11,
                    "coldkey": "coldkey-b",
                    "hotkey": "hotkey-b",
                    "active": True,
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
                    "validator_permit": True,
                    "pruning_score": 8,
                    "stakes": {"alpha": 5.5, "tao": 6.5, "total": 12.0},
                },
                {
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
            ],
        }

    assert mock_turbobt_transport.calls["get_block"] == [(BlockNumber(-1),), (BlockNumber(-1),)]
    assert mock_turbobt_transport.calls["list_neurons"] == [(NetUid(1), block.hash)]
    assert mock_turbobt_transport.calls["get_subnet_state"] == [(NetUid(1), block.hash)]


@pytest.mark.asyncio
async def test_get_validators_open_access_block_not_found(
    patched_test_client: AsyncTestClient,
    mock_turbobt_transport: MockTurboBTtransport,
):
    response = await patched_test_client.get("/api/v1/subnet/1/block/999999/validators")

    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Block 999999 not found.", "status_code": 404}
    assert mock_turbobt_transport.calls["get_block"] == [(BlockNumber(999999),)]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_block_number",
    [
        pytest.param("not_a_number", id="string_value"),
        pytest.param("123.456", id="float_string"),
        pytest.param("true", id="boolean_string"),
    ],
)
async def test_get_validators_open_access_invalid_block_number_type(
    test_client: AsyncTestClient, invalid_block_number: str
):
    response = await test_client.get(f"/api/v1/subnet/1/block/{invalid_block_number}/validators")

    assert response.status_code == HTTP_404_NOT_FOUND, response.content
    assert response.json() == {"status_code": HTTP_404_NOT_FOUND, "detail": "Not Found"}
