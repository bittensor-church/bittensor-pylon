import datetime as dt
from ipaddress import IPv4Address

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_503_SERVICE_UNAVAILABLE
from pylon_commons.constants import BLOCK_PROCESSING_TIME
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
    HotkeyName,
    IdentityName,
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

from pylon_service.bittensor.recent.adapter import CacheKey, _CacheEntry
from pylon_service.identities import identities

_ENDPOINT = "/api/v1/identity/sn1/subnet/1/block/recent/neurons"


@pytest.fixture
def subnet_neurons() -> SubnetNeurons:
    block = Block(number=BlockNumber(123), hash=BlockHash("0xabc123"))
    neuron_a = Neuron(
        uid=NeuronUid(10),
        coldkey=Coldkey("coldkey-a"),
        hotkey=Hotkey("hotkey-a"),
        active=NeuronActive(True),
        axon_info=AxonInfo(ip=IPv4Address("192.168.1.10"), port=Port(8080), protocol=AxonProtocol.HTTP),
        stake=Stake(1.5),
        rank=Rank(0.11),
        emission=Emission(Currency[Token.ALPHA](2.5)),
        incentive=Incentive(0.22),
        consensus=Consensus(0.33),
        trust=Trust(0.44),
        validator_trust=ValidatorTrust(0.55),
        dividends=Dividends(0.66),
        last_update=Timestamp(111),
        validator_permit=ValidatorPermit(True),
        pruning_score=PruningScore(7),
        stakes=Stakes(
            alpha=AlphaStake(Currency[Token.ALPHA](3.5)),
            tao=TaoStake(Currency[Token.TAO](4.5)),
            total=TotalStake(Currency[Token.ALPHA](8.0)),
        ),
    )
    neuron_b = Neuron(
        uid=NeuronUid(11),
        coldkey=Coldkey("coldkey-b"),
        hotkey=Hotkey("hotkey-b"),
        active=NeuronActive(False),
        axon_info=AxonInfo(ip=IPv4Address("10.0.0.2"), port=Port(9090), protocol=AxonProtocol.TCP),
        stake=Stake(9.5),
        rank=Rank(0.77),
        emission=Emission(Currency[Token.ALPHA](1.25)),
        incentive=Incentive(0.88),
        consensus=Consensus(0.99),
        trust=Trust(0.12),
        validator_trust=ValidatorTrust(0.34),
        dividends=Dividends(0.56),
        last_update=Timestamp(222),
        validator_permit=ValidatorPermit(False),
        pruning_score=PruningScore(8),
        stakes=Stakes(
            alpha=AlphaStake(Currency[Token.ALPHA](5.5)),
            tao=TaoStake(Currency[Token.TAO](6.5)),
            total=TotalStake(Currency[Token.ALPHA](12.0)),
        ),
    )
    return SubnetNeurons(block=block, neurons={neuron_a.hotkey: neuron_a, neuron_b.hotkey: neuron_b})


@pytest.fixture
def wallet():
    return identities[IdentityName("sn1")].wallet


@pytest.mark.asyncio
async def test_get_recent_neurons_cache_missing(test_client, mock_recent_objects_store, wallet):
    async with mock_recent_objects_store.behave.mock(get=[None]):
        response = await test_client.get(_ENDPOINT)

        assert response.status_code == HTTP_503_SERVICE_UNAVAILABLE
        assert response.json() == {
            "status_code": HTTP_503_SERVICE_UNAVAILABLE,
            "detail": "Recent neurons data is not available. Cache update may not have finished "
            "yet or subnet may not be configured for caching recent objects.",
        }

    assert mock_recent_objects_store.behave.calls["get"] == [
        (CacheKey(SubnetNeurons, NetUid(1), HotkeyName(wallet.hotkey_str)), None)
    ]


@pytest.mark.asyncio
async def test_get_recent_neurons_cache_expired(test_client, mock_recent_objects_store, subnet_neurons, wallet):
    timestamp = Timestamp(int(dt.datetime.now().timestamp()) - BLOCK_PROCESSING_TIME * 50)  # 40 BLOCK hard limit set.
    cache_entry = _CacheEntry(data=subnet_neurons.model_dump_json(), timestamp=timestamp)
    async with mock_recent_objects_store.behave.mock(get=[cache_entry.model_dump_json().encode()]):
        response = await test_client.get(_ENDPOINT)

        assert response.status_code == HTTP_503_SERVICE_UNAVAILABLE
        assert response.json() == {
            "status_code": HTTP_503_SERVICE_UNAVAILABLE,
            "detail": "Recent neurons data is stale. Cache update may be failing.",
        }

    assert mock_recent_objects_store.behave.calls["get"] == [
        (CacheKey(SubnetNeurons, NetUid(1), HotkeyName(wallet.hotkey_str)), None)
    ]


@pytest.mark.asyncio
async def test_get_recent_neurons_success(test_client, mock_recent_objects_store, subnet_neurons, wallet):
    timestamp = Timestamp(int(dt.datetime.now().timestamp()))
    cache_entry = _CacheEntry(data=subnet_neurons.model_dump_json(), timestamp=timestamp)
    async with mock_recent_objects_store.behave.mock(get=[cache_entry.model_dump_json().encode()]):
        response = await test_client.get(_ENDPOINT)

        assert response.status_code == HTTP_200_OK
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

    assert mock_recent_objects_store.behave.calls["get"] == [
        (CacheKey(SubnetNeurons, NetUid(1), HotkeyName(wallet.hotkey_str)), None)
    ]
