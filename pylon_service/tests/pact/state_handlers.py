import asyncio
import time
from abc import ABC, abstractmethod
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, ClassVar, Literal
from unittest.mock import AsyncMock

from pylon_commons.currency import CurrencyRao, Token
from pylon_commons.models import (
    CommitmentVariant,
    EvmLog,
    HexDataCommitment,
    RevealedCommitment,
    SubnetCommitments,
    SubnetHyperparams,
    SubnetNeurons,
    SubnetPrice,
    SubnetPriceEntry,
    SubnetPrices,
    SubnetRevealedCommitments,
)
from pylon_commons.types import (
    AlphaPriceRao,
    BlockNumber,
    CommitmentDataHex,
    Hotkey,
    NetUid,
    NeuronUid,
    RevealedCommitmentData,
    Tempo,
    Timestamp,
)
from pylon_commons.types import (
    evm as evm_types,
)

from pylon_service.bittensor.exceptions import ArchiveFallbackException
from pylon_service.bittensor.models import RawEvmKeyAssociationInfo
from pylon_service.bittensor.recent.adapter import _CacheEntry
from pylon_service.stores import StoreName
from tests.factories import BlockFactory, EvmAssociationFactory, ExtrinsicFactory, NeuronFactory
from tests.mock_store import MockStore

if TYPE_CHECKING:
    from pytest import MonkeyPatch

    from pylon_service.bittensor.mock_contact import MockBittensorContact
    from pylon_service.evm.mock_contact import MockEvmContact

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
        open_access_client: "MockBittensorContact",
        sn1_client: "MockBittensorContact",
        sn2_client: "MockBittensorContact",
        mock_stores: dict[StoreName, MockStore],
        monkeypatch: "MonkeyPatch",
        mock_evm_contact: "MockEvmContact | None" = None,
    ) -> None:
        self._clients = {
            None: open_access_client,
            "sn1": sn1_client,
            "sn2": sn2_client,
        }
        self.mock_stores = mock_stores
        self.monkeypatch = monkeypatch
        self._evm_contact = mock_evm_contact

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

    def _get_client(self, parameters: dict[str, Any]) -> "MockBittensorContact":
        identity_name = parameters.get("identity_name")
        return self._clients[identity_name]

    @staticmethod
    def _set_default_latest_block(client: "MockBittensorContact", block) -> None:
        client.set_default("get_latest_block", block)

    @abstractmethod
    def setup(self, parameters: dict[str, Any]) -> None:
        pass

    def teardown(self, parameters: dict[str, Any]) -> None:
        for client in self._clients.values():
            client.reset()
        for store in self.mock_stores.values():
            store.reset()
        if self._evm_contact is not None:
            self._evm_contact.reset()
        self.monkeypatch.undo()

    @classmethod
    def create_all(
        cls,
        open_access_client: "MockBittensorContact",
        sn1_client: "MockBittensorContact",
        sn2_client: "MockBittensorContact",
        mock_stores: dict[StoreName, MockStore],
        monkeypatch: "MonkeyPatch",
        mock_evm_contact: "MockEvmContact | None" = None,
    ) -> dict[str, "StateHandler"]:
        return {
            name: handler_cls(open_access_client, sn1_client, sn2_client, mock_stores, monkeypatch, mock_evm_contact)
            for name, handler_cls in _registry.items()
        }


class NeuronsExistHandler(StateHandler):
    name = "neurons exist"

    def setup(self, parameters: dict[str, Any]) -> None:
        block = BlockFactory.build()
        neurons = NeuronFactory.batch(parameters.get("neuron_count", 1))
        subnet_neurons = SubnetNeurons(block=block, neurons={n.hotkey: n for n in neurons})

        client = self._get_client(parameters)
        self._set_default_latest_block(client, block)
        client.add_behavior("get_neurons", subnet_neurons)


class NeuronsExistAtBlockHandler(StateHandler):
    name = "neurons exist at block"

    def setup(self, parameters: dict[str, Any]) -> None:
        block = BlockFactory.build(number=parameters["block_number"])
        neurons = NeuronFactory.batch(parameters.get("neuron_count", 1))
        subnet_neurons = SubnetNeurons(block=block, neurons={n.hotkey: n for n in neurons})

        client = self._get_client(parameters)
        self._set_default_latest_block(client, block)
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
        validators = NeuronFactory.batch(parameters.get("validator_count", 1), validator_permit=True)
        subnet_neurons = SubnetNeurons(block=block, neurons={validator.hotkey: validator for validator in validators})

        client = self._get_client(parameters)
        self._set_default_latest_block(client, block)
        client.add_behavior("get_neurons", subnet_neurons)


class ValidatorsExistAtBlockHandler(StateHandler):
    name = "validators exist at block"

    def setup(self, parameters: dict[str, Any]) -> None:
        block = BlockFactory.build(number=parameters["block_number"])
        validators = NeuronFactory.batch(parameters.get("validator_count", 1), validator_permit=True)
        subnet_neurons = SubnetNeurons(block=block, neurons={validator.hotkey: validator for validator in validators})

        client = self._get_client(parameters)
        self._set_default_latest_block(client, block)
        client.add_behavior("get_block", block)
        client.add_behavior("get_neurons", subnet_neurons)


class CommitmentsExistHandler(StateHandler):
    name = "commitments exist"

    def setup(self, parameters: dict[str, Any]) -> None:
        block = BlockFactory.build()
        commitments: dict[Hotkey, CommitmentVariant] = {
            Hotkey(f"h{i}"): HexDataCommitment(
                commitment_block_number=BlockNumber(block.number - 50),
                hotkey=Hotkey(f"h{i}"),
                commitment=CommitmentDataHex("0xaabbccdd"),
            )
            for i in range(parameters.get("commitment_count", 1))
        }
        subnet_commitments = SubnetCommitments(block=block, commitments=commitments)

        client = self._get_client(parameters)
        self._set_default_latest_block(client, block)
        client.add_behavior("get_commitments", subnet_commitments)
        client.add_behavior("get_subnet_state", SimpleNamespace(hotkeys=list(commitments)))


class CommitmentExistsHandler(StateHandler):
    name = "commitment exists"

    def setup(self, parameters: dict[str, Any]) -> None:
        block = BlockFactory.build()
        hotkey = Hotkey(parameters["hotkey"])
        commitment = HexDataCommitment(
            commitment_block_number=BlockNumber(block.number - 50),
            hotkey=hotkey,
            commitment=CommitmentDataHex("0xaabbccdd"),
        )

        client = self._get_client(parameters)
        self._set_default_latest_block(client, block)
        client.add_behavior("get_commitment", commitment)


class OwnCommitmentExistsHandler(StateHandler):
    name = "own commitment exists"

    def setup(self, parameters: dict[str, Any]) -> None:
        block = BlockFactory.build()
        hotkey = Hotkey(parameters["hotkey"])
        commitment = HexDataCommitment(
            commitment_block_number=BlockNumber(block.number - 50),
            hotkey=hotkey,
            commitment=CommitmentDataHex("0xaabbccdd"),
        )

        client = self._get_client(parameters)
        self._set_default_latest_block(client, block)
        client.add_behavior("get_commitment", commitment)


class LatestBlockInfoExistsHandler(StateHandler):
    name = "latest block info exists"

    def setup(self, parameters: dict[str, Any]) -> None:
        client = self._get_client(parameters)
        self._set_default_latest_block(client, BlockFactory.build())
        client.add_behavior("get_block_timestamp", Timestamp(1700000000))


class ExtrinsicExistsHandler(StateHandler):
    name = "extrinsic exists"

    def setup(self, parameters: dict[str, Any]) -> None:
        block = BlockFactory.build(number=parameters["block_number"])
        extrinsic = ExtrinsicFactory.build(
            block_number=parameters["block_number"],
            extrinsic_index=parameters["extrinsic_index"],
        )

        client = self._get_client(parameters)
        self._set_default_latest_block(client, block)
        client.add_behavior("get_block", block)
        client.add_behavior("get_extrinsic", extrinsic)


class WeightsCanBeSetHandler(StateHandler):
    name = "weights can be set"

    def setup(self, parameters: dict[str, Any]) -> None:
        self.monkeypatch.setattr("pylon_service.api._unstable.tasks.ApplyWeights.schedule", AsyncMock())


class BlockDataUnavailableHandler(StateHandler):
    name = "block data unavailable"

    def setup(self, parameters: dict[str, Any]) -> None:
        block = BlockFactory.build(number=parameters["block_number"])

        client = self._get_client(parameters)
        self._set_default_latest_block(client, block)
        client.add_behavior("get_block", block)
        client.add_behavior(
            "get_neurons",
            ArchiveFallbackException(
                detail=f"Block {parameters['block_number']} data is unavailable on both main and archive nodes."
            ),
        )


class CommitmentCanBeSetHandler(StateHandler):
    name = "commitment can be set"

    def setup(self, parameters: dict[str, Any]) -> None:
        block = BlockFactory.build()
        client = self._get_client(parameters)
        self._set_default_latest_block(client, block)
        client.add_behavior("set_commitment", None)


class RevealedCommitmentsExistHandler(StateHandler):
    name = "revealed commitments exist"

    def setup(self, parameters: dict[str, Any]) -> None:
        block = BlockFactory.build()
        client = self._get_client(parameters)
        self._set_default_latest_block(client, block)

        if "hotkey" in parameters:
            hotkey = Hotkey(parameters["hotkey"])
            commitments: list[RevealedCommitment] = [
                RevealedCommitment(
                    reveal_block_number=BlockNumber(block.number - 50),
                    hotkey=hotkey,
                    commitment=RevealedCommitmentData("0xaabbccdd11223344"),
                )
            ]
            client.add_behavior("get_revealed_commitments", commitments)
        else:
            hotkeys = [Hotkey("h1"), Hotkey("h2")]
            commitments_dict: dict[Hotkey, list[RevealedCommitment]] = {
                hotkey: [
                    RevealedCommitment(
                        reveal_block_number=BlockNumber(block.number - 50),
                        hotkey=hotkey,
                        commitment=RevealedCommitmentData("0xaabbccdd11223344"),
                    )
                ]
                for hotkey in hotkeys
            }
            subnet_revealed_commitments = SubnetRevealedCommitments(block=block, commitments=commitments_dict)
            client.add_behavior("get_all_revealed_commitments", subnet_revealed_commitments)


class OwnRevealedCommitmentsExistHandler(StateHandler):
    name = "own revealed commitments exist"

    def setup(self, parameters: dict[str, Any]) -> None:
        block = BlockFactory.build()
        hotkey = Hotkey(parameters["hotkey"])
        commitments: list[RevealedCommitment] = [
            RevealedCommitment(
                reveal_block_number=BlockNumber(block.number - 50),
                hotkey=hotkey,
                commitment=RevealedCommitmentData("0xaabbccdd11223344"),
            )
        ]

        client = self._get_client(parameters)
        self._set_default_latest_block(client, block)
        client.add_behavior("get_revealed_commitments", commitments)


class RevealedCommitmentCanBeSetHandler(StateHandler):
    name = "revealed commitment can be set"

    def setup(self, parameters: dict[str, Any]) -> None:
        block = BlockFactory.build()
        client = self._get_client(parameters)
        self._set_default_latest_block(client, block)
        client.add_behavior("set_revealed_commitment", 123456)


class WeightsStatusExistsHandler(StateHandler):
    name = "weights status can be retrieved"

    def setup(self, parameters: dict[str, Any]) -> None:
        block_number = int(parameters.get("block_number", 789))
        block = BlockFactory.build(number=block_number)
        hyperparams = SubnetHyperparams(tempo=Tempo(360))

        client = self._get_client(parameters)
        self._set_default_latest_block(client, block)
        client.add_behavior("get_block", block)
        client.add_behavior("get_hyperparams", hyperparams)


class EvmAssociationsExistHandler(StateHandler):
    name = "evm associations exist"

    def setup(self, parameters: dict[str, Any]) -> None:
        block = BlockFactory.build()
        association_count = parameters.get("association_count", 1)
        hotkeys = [Hotkey(f"h{i}") for i in range(association_count)]

        associations = {
            NeuronUid(i): RawEvmKeyAssociationInfo(
                evm_address=EvmAssociationFactory.build().evm_address,
                last_block_where_ownership_was_proven=BlockNumber(block.number - 10),
            )
            for i in range(association_count)
        }

        client = self._get_client(parameters)
        self._set_default_latest_block(client, block)
        client.add_behavior("get_evm_key_associations", associations)
        client.add_behavior("get_subnet_state", SimpleNamespace(hotkeys=hotkeys))


class BittensorHangs(StateHandler):
    name = "bittensor hangs"

    def setup(self, parameters: dict[str, Any]) -> None:
        seconds = parameters["seconds"]

        async def hang(*_args, **_kwargs):
            await asyncio.sleep(seconds)

        client = self._get_client(parameters)
        client.add_behavior(parameters["method"], hang)


def _build_subnet_prices(block) -> SubnetPrices:
    return SubnetPrices(
        block=block,
        prices={
            NetUid(1): SubnetPriceEntry(value=AlphaPriceRao(CurrencyRao[Token.TAO](1_000_000))),
            NetUid(2): SubnetPriceEntry(value=AlphaPriceRao(CurrencyRao[Token.TAO](2_000_000))),
        },
    )


class PricesExistHandler(StateHandler):
    name = "prices exist"

    def setup(self, parameters: dict[str, Any]) -> None:
        block = BlockFactory.build()
        prices = _build_subnet_prices(block)
        client = self._get_client(parameters)
        self._set_default_latest_block(client, block)
        client.add_behavior("get_alpha_prices", prices)


class PricesExistAtBlockHandler(StateHandler):
    name = "prices exist at block"

    def setup(self, parameters: dict[str, Any]) -> None:
        block = BlockFactory.build(number=parameters["block_number"])
        prices = _build_subnet_prices(block)
        client = self._get_client(parameters)
        self._set_default_latest_block(client, block)
        client.add_behavior("get_block", block)
        client.add_behavior("get_alpha_prices", prices)


class PriceExistsHandler(StateHandler):
    name = "price exists"

    def setup(self, parameters: dict[str, Any]) -> None:
        block = BlockFactory.build()
        netuid = NetUid(parameters.get("netuid", 1))
        price = SubnetPrice(
            block=block,
            netuid=netuid,
            price=SubnetPriceEntry(value=AlphaPriceRao(CurrencyRao[Token.TAO](1_000_000))),
        )
        client = self._get_client(parameters)
        self._set_default_latest_block(client, block)
        client.add_behavior("get_alpha_price", price)


class PriceExistsAtBlockHandler(StateHandler):
    name = "price exists at block"

    def setup(self, parameters: dict[str, Any]) -> None:
        block = BlockFactory.build(number=parameters["block_number"])
        netuid = NetUid(parameters.get("netuid", 1))
        price = SubnetPrice(
            block=block,
            netuid=netuid,
            price=SubnetPriceEntry(value=AlphaPriceRao(CurrencyRao[Token.TAO](1_000_000))),
        )
        client = self._get_client(parameters)
        self._set_default_latest_block(client, block)
        client.add_behavior("get_block", block)
        client.add_behavior("get_alpha_price", price)


class EvmContractLogsExistHandler(StateHandler):
    name = "evm contract logs exist"

    def setup(self, parameters: dict[str, Any]) -> None:
        assert self._evm_contact is not None
        self._evm_contact.add_behavior("get_current_block", evm_types.BlockNumber(1000))
        self._evm_contact.add_behavior(
            "get_logs",
            [
                EvmLog(
                    event="Transfer",
                    args={"from": "0xaaaa", "to": "0xbbbb", "value": 1000},
                    address=evm_types.Address("0x" + "d" * 40),
                    block_number=evm_types.BlockNumber(1000),
                    transaction_hash=evm_types.TransactionHash("0x" + "e" * 64),
                    transaction_index=evm_types.TransactionIndex(0),
                    log_index=evm_types.LogIndex(0),
                )
            ],
        )


class NoEvmContractLogsExistHandler(StateHandler):
    name = "no evm contract logs exist"

    def setup(self, parameters: dict[str, Any]) -> None:
        assert self._evm_contact is not None
        self._evm_contact.add_behavior("get_current_block", evm_types.BlockNumber(1000))
        self._evm_contact.add_behavior("get_logs", [])
