"""
Shared fixtures for transport-seam tests under new_tests/.
"""

from contextlib import asynccontextmanager
from datetime import timedelta
from ipaddress import IPv4Address
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

import pytest
import pytest_asyncio
from litestar.stores.base import Store
from litestar.testing import AsyncTestClient
from pylon_commons.currency import Currency, Token
from pylon_commons.models import AxonInfo, AxonProtocol, Block, Neuron, Stakes, SubnetNeurons, SubnetValidators
from pylon_commons.types import (
    AlphaStake,
    BittensorNetwork,
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
from turbobt.client import Bittensor
from turbobt.neuron import Neuron as TurboBtNeuron
from turbobt.subnet import SubnetState as TurboBtSubnetState

from pylon_service import lifespans, main
from pylon_service.bittensor.client import MockTurboBTtransport
from pylon_service.bittensor.pool import BittensorClientPool
from pylon_service.main import create_app
from pylon_service.stores import StoreName

# These fixtures intentionally duplicate a subset of the older test setup.
# This directory is the start of a gradual migration away from pylon_service/tests/,
# so tests here must not inherit the shared MockBittensorClient-based pool seam.


class MockStore(Store):
    def __init__(self) -> None:
        self.data: dict[str, bytes] = {}

    async def set(self, key: str, value: str | bytes, expires_in: int | timedelta | None = None) -> None:
        self.data[key] = value.encode() if isinstance(value, str) else value

    async def get(self, key: str, renew_for: int | timedelta | None = None) -> bytes | None:
        return self.data.get(key)

    async def delete(self, key: str) -> None:
        self.data.pop(key, None)

    async def delete_all(self) -> None:
        self.data.clear()

    async def exists(self, key: str) -> bool:
        return key in self.data

    async def expires_in(self, key: str) -> int | None:
        return None

    def reset(self) -> None:
        self.data.clear()


def _build_default_neuron(
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
def turbobt_block_builder():
    def build(number: int, block_hash: str) -> TurboBtBlock:
        return TurboBtBlock(block_hash, number, client=cast(Bittensor, None))

    return build


@pytest.fixture
def turbobt_neuron_builder():
    def build(neuron: Neuron) -> TurboBtNeuron:
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

    return build


@pytest.fixture
def raw_subnet_state_builder():
    def build(netuid: NetUid, subnet_state: SubnetNeurons | SubnetValidators) -> TurboBtSubnetState:
        items = (
            list(subnet_state.neurons.values()) if isinstance(subnet_state, SubnetNeurons) else subnet_state.validators
        )
        return cast(
            TurboBtSubnetState,
            {
                "netuid": netuid,
                "hotkeys": [item.hotkey for item in items],
                "coldkeys": [item.coldkey for item in items],
                "active": [item.active for item in items],
                "validator_permit": [item.validator_permit for item in items],
                "pruning_score": [item.pruning_score for item in items],
                "last_update": [item.last_update for item in items],
                "emission": [Currency[Token.ALPHA](item.emission).as_rao() for item in items],
                "dividends": [item.dividends for item in items],
                "incentives": [item.incentive for item in items],
                "consensus": [item.consensus for item in items],
                "trust": [item.trust for item in items],
                "rank": [item.rank for item in items],
                "block_at_registration": [BlockNumber(0) for _ in items],
                "alpha_stake": [Currency[Token.ALPHA](item.stakes.alpha).as_rao() for item in items],
                "tao_stake": [Currency[Token.TAO](item.stakes.tao).as_rao() for item in items],
                "total_stake": [Currency[Token.ALPHA](item.stakes.total).as_rao() for item in items],
                "emission_history": [[Currency[Token.ALPHA](item.emission).as_rao()] for item in items],
            },
        )

    return build


@pytest.fixture
def default_netuid() -> NetUid:
    return NetUid(1)


@pytest.fixture
def default_block() -> Block:
    return Block(number=BlockNumber(123), hash=BlockHash("0xabc123"))


@pytest.fixture
def default_raw_block(default_block: Block, turbobt_block_builder) -> TurboBtBlock:
    return turbobt_block_builder(int(default_block.number), str(default_block.hash))


@pytest.fixture
def default_subnet_neurons(default_block: Block) -> SubnetNeurons:
    neuron_a = _build_default_neuron(
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
    neuron_b = _build_default_neuron(
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
    return SubnetNeurons(block=default_block, neurons={neuron_a.hotkey: neuron_a, neuron_b.hotkey: neuron_b})


@pytest.fixture
def default_raw_neurons(default_subnet_neurons: SubnetNeurons, turbobt_neuron_builder) -> list[TurboBtNeuron]:
    return [turbobt_neuron_builder(neuron) for neuron in default_subnet_neurons.neurons.values()]


@pytest.fixture
def default_raw_subnet_state(
    default_netuid: NetUid,
    default_subnet_neurons: SubnetNeurons,
    raw_subnet_state_builder,
) -> TurboBtSubnetState:
    return raw_subnet_state_builder(default_netuid, default_subnet_neurons)


@pytest.fixture
def additional_transport_seed_instructions() -> list[tuple[NetUid, Block, list[TurboBtNeuron], dict[str, object]]]:
    return []


@pytest.fixture
def mock_turbobt_transport() -> MockTurboBTtransport:
    return MockTurboBTtransport()


@pytest.fixture(autouse=True)
def seed_mock_turbobt_transport(
    mock_turbobt_transport: MockTurboBTtransport,
    default_netuid: NetUid,
    default_block: Block,
    default_raw_block: TurboBtBlock,
    default_raw_neurons: list[TurboBtNeuron],
    default_raw_subnet_state: TurboBtSubnetState,
    additional_transport_seed_instructions: list[tuple[NetUid, Block, list[TurboBtNeuron], TurboBtSubnetState]],
) -> None:
    mock_turbobt_transport.set_latest_block(default_raw_block)
    mock_turbobt_transport.add_block(default_raw_block)
    mock_turbobt_transport.add_neurons_range(default_netuid, int(default_block.number), None, default_raw_neurons)
    mock_turbobt_transport.add_subnet_state_range(
        default_netuid,
        int(default_block.number),
        None,
        default_raw_subnet_state,
    )
    for netuid, block, raw_neurons, raw_subnet_state in additional_transport_seed_instructions:
        raw_block = TurboBtBlock(str(block.hash), int(block.number), client=cast(Bittensor, None))
        mock_turbobt_transport.add_block(raw_block)
        mock_turbobt_transport.add_neurons_range(netuid, int(block.number), None, raw_neurons)
        mock_turbobt_transport.add_subnet_state_range(netuid, int(block.number), None, raw_subnet_state)


@pytest_asyncio.fixture
async def bt_client_pool(mock_turbobt_transport: MockTurboBTtransport):
    with patch(
        "pylon_service.bittensor.client.get_turbobt_transport",
        return_value=mock_turbobt_transport,
    ):
        async with BittensorClientPool(
            uri=BittensorNetwork("ws://localhost:8000"),
            archive_uri=BittensorNetwork("ws://localhost:8001"),
        ) as pool:
            yield pool


@pytest.fixture(scope="session")
def mock_stores():
    return {StoreName.RECENT_OBJECTS: MockStore()}


@pytest.fixture(autouse=True)
def reset_mock_stores(mock_stores):
    yield
    for store in mock_stores.values():
        store.reset()


@pytest.fixture
def test_app(bt_client_pool, mock_stores):
    @asynccontextmanager
    async def mock_lifespan(app):
        app.state.bittensor_client_pool = bt_client_pool
        yield

    @asynccontextmanager
    async def mock_scheduler_lifespan(app):
        yield

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(lifespans, "bittensor_client_pool", mock_lifespan)
        monkeypatch.setattr(lifespans, "scheduler_lifespan", mock_scheduler_lifespan)
        monkeypatch.setattr(main, "stores", {**mock_stores})

        app = create_app()
        app.response_cache_config.cache_response_filter = lambda _, __: False
        app.debug = True
        yield app


@pytest_asyncio.fixture
async def test_client(test_app):
    async with AsyncTestClient(app=test_app) as client:
        yield client
