import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, Literal
from unittest.mock import AsyncMock

from pylon_commons.models import Commitment, SubnetCommitments, SubnetNeurons, SubnetValidators
from pylon_commons.types import CommitmentDataHex, Hotkey, Timestamp

from pylon_service.bittensor.recent.adapter import _CacheEntry
from pylon_service.stores import StoreName
from tests.factories import BlockFactory, ExtrinsicFactory, NeuronFactory
from tests.mock_store import MockStore

if TYPE_CHECKING:
    from pytest import MonkeyPatch

    from tests.mock_bittensor_client import MockBittensorClient

_registry: dict[str, type["StateHandler"]] = {}


class StateHandler(ABC):
    """
    Base class for Pact provider state handlers.

    Pact state handlers configure mock behavior before each contract interaction is verified.
    Subclasses define a `name` class variable matching the provider state string in pact files,
    and implement `setup()` to configure the mock client's behavior for that state.

    Subclasses are auto-registered via `__init_subclass__` and instantiated via `create_all()`.
    """

    name: ClassVar[str]

    def __init__(
        self,
        open_access_client: "MockBittensorClient",
        sn1_client: "MockBittensorClient",
        sn2_client: "MockBittensorClient",
        mock_stores: dict[StoreName, MockStore],
        monkeypatch: "MonkeyPatch",
    ) -> None:
        self._clients = {
            None: open_access_client,
            "sn1": sn1_client,
            "sn2": sn2_client,
        }
        self.mock_stores = mock_stores
        self.monkeypatch = monkeypatch

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        if ABC in cls.__bases__:
            return
        if not hasattr(cls, "name") or not cls.name:
            raise TypeError(f"StateHandler subclass {cls.__name__} must define 'name'")
        if cls.name in _registry:
            raise ValueError(f"StateHandler '{cls.name}' already registered")
        _registry[cls.name] = cls

    def __call__(self, action: Literal["setup", "teardown"], parameters: dict[str, Any] | None) -> None:
        parameters = parameters or {}
        if action == "setup":
            self.setup(parameters)
        elif action == "teardown":
            self.teardown(parameters)

    def _get_client(self, parameters: dict[str, Any]) -> "MockBittensorClient":
        identity_name = parameters.get("identity_name")
        return self._clients[identity_name]

    @abstractmethod
    def setup(self, parameters: dict[str, Any]) -> None:
        pass

    def teardown(self, parameters: dict[str, Any]) -> None:
        for client in self._clients.values():
            client.reset()
        for store in self.mock_stores.values():
            store.reset()
        self.monkeypatch.undo()

    @classmethod
    def create_all(
        cls,
        open_access_client: "MockBittensorClient",
        sn1_client: "MockBittensorClient",
        sn2_client: "MockBittensorClient",
        mock_stores: dict[StoreName, MockStore],
        monkeypatch: "MonkeyPatch",
    ) -> dict[str, "StateHandler"]:
        return {
            name: handler_cls(open_access_client, sn1_client, sn2_client, mock_stores, monkeypatch)
            for name, handler_cls in _registry.items()
        }


class NeuronsExistHandler(StateHandler):
    name = "neurons exist"

    def setup(self, parameters: dict[str, Any]) -> None:
        block = BlockFactory.build()
        neurons = NeuronFactory.batch(parameters.get("neuron_count", 1))
        subnet_neurons = SubnetNeurons(block=block, neurons={n.hotkey: n for n in neurons})

        client = self._get_client(parameters)
        client.add_behavior("get_latest_block", block)
        client.add_behavior("get_neurons", subnet_neurons)


class NeuronsExistAtBlockHandler(StateHandler):
    name = "neurons exist at block"

    def setup(self, parameters: dict[str, Any]) -> None:
        block = BlockFactory.build(number=parameters["block_number"])
        neurons = NeuronFactory.batch(parameters.get("neuron_count", 1))
        subnet_neurons = SubnetNeurons(block=block, neurons={n.hotkey: n for n in neurons})

        client = self._get_client(parameters)
        client.add_behavior("get_block", block)
        client.add_behavior("get_neurons", subnet_neurons)


class RecentNeuronsExistHandler(StateHandler):
    name = "recent neurons exist"

    def setup(self, parameters: dict[str, Any]) -> None:
        block = BlockFactory.build()
        neurons = NeuronFactory.batch(parameters.get("neuron_count", 1))
        subnet_neurons = SubnetNeurons(block=block, neurons={n.hotkey: n for n in neurons})

        cache_entry = _CacheEntry(data=subnet_neurons.model_dump_json(), timestamp=Timestamp(int(time.time())))
        self.mock_stores[StoreName.RECENT_OBJECTS].behave.add_behavior("get", cache_entry.model_dump_json().encode())


class ValidatorsExistHandler(StateHandler):
    name = "validators exist"

    def setup(self, parameters: dict[str, Any]) -> None:
        block = BlockFactory.build()
        validators = NeuronFactory.batch(parameters.get("validator_count", 1))
        subnet_validators = SubnetValidators(block=block, validators=validators)

        client = self._get_client(parameters)
        client.add_behavior("get_latest_block", block)
        client.add_behavior("get_validators", subnet_validators)


class ValidatorsExistAtBlockHandler(StateHandler):
    name = "validators exist at block"

    def setup(self, parameters: dict[str, Any]) -> None:
        block = BlockFactory.build(number=parameters["block_number"])
        validators = NeuronFactory.batch(parameters.get("validator_count", 1))
        subnet_validators = SubnetValidators(block=block, validators=validators)

        client = self._get_client(parameters)
        client.add_behavior("get_block", block)
        client.add_behavior("get_validators", subnet_validators)


class CommitmentsExistHandler(StateHandler):
    name = "commitments exist"

    def setup(self, parameters: dict[str, Any]) -> None:
        block = BlockFactory.build()
        commitments = {
            Hotkey(f"h{i}"): CommitmentDataHex("0xaabbccdd") for i in range(parameters.get("commitment_count", 1))
        }
        subnet_commitments = SubnetCommitments(block=block, commitments=commitments)

        client = self._get_client(parameters)
        client.add_behavior("get_latest_block", block)
        client.add_behavior("get_commitments", subnet_commitments)


class CommitmentExistsHandler(StateHandler):
    name = "commitment exists"

    def setup(self, parameters: dict[str, Any]) -> None:
        block = BlockFactory.build()
        hotkey = Hotkey(parameters["hotkey"])
        commitment = Commitment(
            block=block,
            hotkey=hotkey,
            commitment=CommitmentDataHex("0xaabbccdd"),
        )

        client = self._get_client(parameters)
        client.add_behavior("get_latest_block", block)
        client.add_behavior("get_commitment", commitment)


class OwnCommitmentExistsHandler(StateHandler):
    name = "own commitment exists"

    def setup(self, parameters: dict[str, Any]) -> None:
        block = BlockFactory.build()
        hotkey = Hotkey(parameters["hotkey"])
        commitment = Commitment(
            block=block,
            hotkey=hotkey,
            commitment=CommitmentDataHex("0xaabbccdd"),
        )

        client = self._get_client(parameters)
        client.add_behavior("get_latest_block", block)
        client.add_behavior("get_commitment", commitment)


class ExtrinsicExistsHandler(StateHandler):
    name = "extrinsic exists"

    def setup(self, parameters: dict[str, Any]) -> None:
        block = BlockFactory.build(number=parameters["block_number"])
        extrinsic = ExtrinsicFactory.build(
            block_number=parameters["block_number"],
            extrinsic_index=parameters["extrinsic_index"],
        )

        client = self._get_client(parameters)
        client.add_behavior("get_block", block)
        client.add_behavior("get_extrinsic", extrinsic)


class WeightsCanBeSetHandler(StateHandler):
    name = "weights can be set"

    def setup(self, parameters: dict[str, Any]) -> None:
        self.monkeypatch.setattr("pylon_service.api.ApplyWeights.schedule", AsyncMock())


class CommitmentCanBeSetHandler(StateHandler):
    name = "commitment can be set"

    def setup(self, parameters: dict[str, Any]) -> None:
        block = BlockFactory.build()
        client = self._get_client(parameters)
        client.add_behavior("get_latest_block", block)
        client.add_behavior("set_commitment", None)
