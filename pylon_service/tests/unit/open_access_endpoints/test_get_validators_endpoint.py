"""
Tests for the GET /subnet/{netuid}/block/{block_number}/validators endpoint.
"""

from ipaddress import IPv4Address

import pytest
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

from tests.mock_bittensor_client import MockBittensorClient


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


@pytest.fixture
def block() -> Block:
    return Block(number=BlockNumber(123), hash=BlockHash("0xabc123"))


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


@pytest.mark.asyncio
async def test_get_validators_open_access_success(
    test_client: AsyncTestClient,
    open_access_mock_bt_client: MockBittensorClient,
    block: Block,
    subnet_validators: SubnetValidators,
):
    async with open_access_mock_bt_client.mock_behavior(get_block=[block], get_validators=[subnet_validators]):
        response = await test_client.get(f"/api/v1/subnet/1/block/{block.number}/validators")

        assert response.status_code == HTTP_200_OK
        assert response.json() == {
            "block": {"number": 123, "hash": "0xabc123"},
            "validators": [
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
            ],
        }

    assert open_access_mock_bt_client.calls["get_block"] == [(block.number,)]
    assert open_access_mock_bt_client.calls["get_validators"] == [(NetUid(1), block)]


@pytest.mark.asyncio
async def test_get_latest_validators_open_access_success(
    test_client: AsyncTestClient,
    open_access_mock_bt_client: MockBittensorClient,
    block: Block,
    subnet_validators: SubnetValidators,
):
    async with open_access_mock_bt_client.mock_behavior(
        get_latest_block=[block],
        get_validators=[subnet_validators],
    ):
        response = await test_client.get("/api/v1/subnet/1/block/latest/validators")

        assert response.status_code == HTTP_200_OK
        assert response.json() == {
            "block": {"number": 123, "hash": "0xabc123"},
            "validators": [
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
            ],
        }

    assert open_access_mock_bt_client.calls["get_latest_block"] == [()]
    assert open_access_mock_bt_client.calls["get_validators"] == [(NetUid(1), block)]


@pytest.mark.asyncio
async def test_get_validators_open_access_block_not_found(
    test_client: AsyncTestClient,
    open_access_mock_bt_client: MockBittensorClient,
):
    async with open_access_mock_bt_client.mock_behavior(
        get_block=[None],
    ):
        response = await test_client.get("/api/v1/subnet/1/block/999999/validators")

        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "Block 999999 not found.", "status_code": 404}


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
