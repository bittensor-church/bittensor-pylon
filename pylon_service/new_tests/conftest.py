"""
Shared fixtures for transport-seam tests under new_tests/.
"""

from contextlib import asynccontextmanager
from datetime import timedelta
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

import pytest
import pytest_asyncio
from litestar.testing import AsyncTestClient
from litestar.stores.base import Store
from pylon_commons.currency import Currency, Token
from pylon_commons.models import Neuron, SubnetNeurons, SubnetValidators
from pylon_commons.types import BittensorNetwork, BlockNumber, NetUid
from turbobt.block import Block as TurboBtBlock
from turbobt.neuron import Neuron as TurboBtNeuron

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


@pytest.fixture
def turbobt_block_builder():
    def build(number: int, block_hash: str) -> TurboBtBlock:
        return TurboBtBlock(block_hash, number, client=None)

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
    def build(netuid: NetUid, subnet_state: SubnetNeurons | SubnetValidators) -> dict[str, object]:
        items = list(subnet_state.neurons.values()) if isinstance(subnet_state, SubnetNeurons) else subnet_state.validators
        return {
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
        }

    return build


@pytest.fixture
def mock_turbobt_transport() -> MockTurboBTtransport:
    return MockTurboBTtransport()


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
