from __future__ import annotations

import asyncio
import inspect
from collections import defaultdict
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any

from pylon_commons.models import CommitmentVariant, RevealedCommitment, SubnetRevealedCommitments
from pylon_commons.types import (
    BittensorNetwork,
    BlockNumber,
    CommitmentDataBytes,
    ExtrinsicIndex,
    Hotkey,
    MechanismId,
    NetUid,
    NeuronUid,
    RevealedCommitmentData,
    RevealRound,
    Timestamp,
    Weight,
)

from pylon_service.bittensor.contact import AbstractBittensorContact
from pylon_service.bittensor.models import (
    Block,
    CertificateAlgorithm,
    Extrinsic,
    Neuron,
    NeuronCertificate,
    NeuronCertificateKeypair,
    SubnetCommitments,
    SubnetHyperparams,
    SubnetNeurons,
    SubnetPrice,
    SubnetPrices,
    SubnetState,
)

type Behavior = Callable | Exception | Any
type MethodName = str
type Call = tuple


class Behave:
    """
    A reusable behavior mocker that 'behaves' in the configured way when called.
    It can be used to create mock implementations from abstract classes for testing.
    The behavior can be verified through recorded calls and tests.

    Example usage:
    One can add an instance of this class to a concrete implementation class, and record
    calls act according to configured behaviors.
    class MockConcreteClass(AbstractClass):
        def __init__(self):
            self.behave = Behave()

        def method_to_mock(self, arg1, arg2):
            self.behave.track("method_to_mock", arg1, arg2)
            return self.behave.execute("method_to_mock", arg1, arg2)

    # In the test:
    mock_instance = MockConcreteClass()

    async with mock_instance.behave.mock(method_to_mock=[1, Exception("Error")]):
        assert mock_instance.method_to_mock("A", "B") == 1
        with pytest.raises(Exception, match="Error"):
            mock_instance.method_to_mock("C", "D")

    assert mock_instance.behave.calls["method_to_mock"] == [("A", "B"), ("C", "D")]
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._behaviors: dict[MethodName, list[Behavior]] = defaultdict(list)
        self.calls: dict[MethodName, list[Call]] = defaultdict(list)

    @asynccontextmanager
    async def mock(self, **behaviors: list[Behavior] | Behavior):
        for method_name, behavior in behaviors.items():
            if not isinstance(behavior, list):
                self._behaviors[method_name].append(behavior)
            else:
                self._behaviors[method_name].extend(behavior)

        try:
            yield
        finally:
            self._behaviors.clear()

    async def execute(self, method_name: str, *args, **kwargs) -> Any:
        async with self._lock:
            if not self._behaviors[method_name]:
                raise NotImplementedError(
                    f"No mock behavior configured for {method_name}. "
                    f"Use mock_behavior() context manager to configure it."
                )

            behavior = self._behaviors[method_name].pop(0)

        if isinstance(behavior, Exception):
            raise behavior

        if callable(behavior):
            result = behavior(*args, **kwargs)
            if inspect.iscoroutine(result):
                return await result

            return result

        return behavior

    def track(self, method_name: str, *args, **kwargs) -> None:
        if kwargs:
            self.calls[method_name].append((args, kwargs))
        else:
            self.calls[method_name].append(args)

    def add_behavior(self, method_name: str, behavior: Behavior) -> None:
        self._behaviors[method_name].append(behavior)

    def reset(self) -> None:
        self.calls.clear()
        self._behaviors.clear()


class MockBittensorContact(AbstractBittensorContact):
    def __init__(self, wallet: Any | None = None, uri: BittensorNetwork = BittensorNetwork("mock://test")):
        super().__init__(wallet=wallet, uri=uri)
        self._behave = Behave()
        self._is_open = False
        self._defaults: dict[str, Behavior] = {}

    async def open(self) -> None:
        self._is_open = True

    async def close(self) -> None:
        self._is_open = False

    async def recreate(self) -> None:
        pass

    @asynccontextmanager
    async def mock_behavior(self, **behaviors: list[Behavior] | Behavior):
        async with self._behave.mock(**behaviors):
            yield

    def add_behavior(self, method_name: str, behavior: Behavior) -> None:
        self._behave.add_behavior(method_name, behavior)

    def set_default(self, method_name: str, behavior: Behavior) -> None:
        self._defaults[method_name] = behavior

    def reset(self) -> None:
        self._behave.reset()
        self._defaults.clear()

    @property
    def calls(self):
        return self._behave.calls

    async def _execute_behavior(self, method_name: str, *args, **kwargs) -> Any:
        self._behave.track(method_name, *args, **kwargs)
        try:
            return await self._behave.execute(method_name, *args, **kwargs)
        except NotImplementedError:
            if method_name not in self._defaults:
                raise

        behavior = self._defaults[method_name]
        if isinstance(behavior, Exception):
            raise behavior
        if callable(behavior):
            result = behavior(*args, **kwargs)
            if inspect.iscoroutine(result):
                return await result
            return result
        return behavior

    async def get_block(self, number: BlockNumber) -> Block | None:
        return await self._execute_behavior("get_block", number)

    async def get_latest_block(self) -> Block:
        return await self._execute_behavior("get_latest_block")

    async def get_block_timestamp(self, block: Block) -> Timestamp:
        return await self._execute_behavior("get_block_timestamp", block)

    async def get_neurons_list(self, netuid: NetUid, block: Block) -> list[Neuron]:
        return await self._execute_behavior("get_neurons_list", netuid, block)

    async def get_hyperparams(self, netuid: NetUid, block: Block) -> SubnetHyperparams | None:
        return await self._execute_behavior("get_hyperparams", netuid, block)

    async def get_certificates(self, netuid: NetUid, block: Block) -> dict[Hotkey, NeuronCertificate]:
        return await self._execute_behavior("get_certificates", netuid, block)

    async def get_certificate(
        self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None
    ) -> NeuronCertificate | None:
        return await self._execute_behavior("get_certificate", netuid, block, hotkey)

    async def generate_certificate_keypair(
        self, netuid: NetUid, algorithm: CertificateAlgorithm
    ) -> NeuronCertificateKeypair | None:
        return await self._execute_behavior("generate_certificate_keypair", netuid, algorithm)

    async def get_subnet_state(self, netuid: NetUid, block: Block) -> SubnetState:
        return await self._execute_behavior("get_subnet_state", netuid, block)

    async def commit_weights(
        self, netuid: NetUid, mechanism_id: MechanismId, weights: dict[NeuronUid, Weight]
    ) -> RevealRound:
        return await self._execute_behavior("commit_weights", netuid, mechanism_id, weights)

    async def set_weights(self, netuid: NetUid, mechanism_id: MechanismId, weights: dict[NeuronUid, Weight]) -> None:
        return await self._execute_behavior("set_weights", netuid, mechanism_id, weights)

    async def get_neurons(self, netuid: NetUid, block: Block) -> SubnetNeurons:
        return await self._execute_behavior("get_neurons", netuid, block)

    async def get_alpha_prices(self, block: Block) -> SubnetPrices:
        return await self._execute_behavior("get_alpha_prices", block)

    async def get_alpha_price(self, netuid: NetUid, block: Block) -> SubnetPrice:
        return await self._execute_behavior("get_alpha_price", netuid, block)

    async def get_commitment(
        self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None
    ) -> CommitmentVariant | None:
        return await self._execute_behavior("get_commitment", netuid, block, hotkey)

    async def get_commitments(self, netuid: NetUid, block: Block) -> SubnetCommitments:
        return await self._execute_behavior("get_commitments", netuid, block)

    async def set_commitment(self, netuid: NetUid, data: CommitmentDataBytes) -> None:
        return await self._execute_behavior("set_commitment", netuid, data)

    async def get_extrinsic(self, block: Block, extrinsic_index: ExtrinsicIndex) -> Extrinsic | None:
        return await self._execute_behavior("get_extrinsic", block, extrinsic_index)

    async def get_revealed_commitments(
        self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None
    ) -> list[RevealedCommitment] | None:
        return await self._execute_behavior("get_revealed_commitments", netuid, block, hotkey)

    async def get_all_revealed_commitments(self, netuid: NetUid, block: Block) -> SubnetRevealedCommitments:
        return await self._execute_behavior("get_all_revealed_commitments", netuid, block)

    async def set_revealed_commitment(
        self, netuid: NetUid, commitment: RevealedCommitmentData, block_to_reveal: int
    ) -> int:
        return await self._execute_behavior("set_revealed_commitment", netuid, commitment, block_to_reveal)

    async def get_drand_last_stored_round(self, block: Block | None = None) -> int:
        return await self._execute_behavior("get_drand_last_stored_round", block)
