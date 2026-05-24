# FileBacked dev models intentionally narrow inherited pydantic fields (e.g. axon_info, stakes, block).
# pyright: reportIncompatibleVariableOverride=false
from pathlib import Path
from typing import Any

import yaml
from pydantic import model_validator

from pylon_client._internal.pylon_commons._unstable.models import AxonInfo, AxonProtocol, Block, Neuron, Stakes
from pylon_client._internal.pylon_commons._unstable.responses import GetNeuronsResponse
from pylon_client._internal.pylon_commons.currency import Currency, Token
from pylon_client._internal.pylon_commons.types import (
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


class _FileBackedAxonInfo(AxonInfo):
    """
    AxonInfo for local development: only ip and port are required, protocol defaults to HTTP.
    """

    protocol: AxonProtocol = AxonProtocol.HTTP


class _FileBackedStakes(Stakes):
    """
    Stakes for local development: all amounts default to zero.
    """

    alpha: AlphaStake = AlphaStake(Currency[Token.ALPHA](0.0))
    tao: TaoStake = TaoStake(Currency[Token.TAO](0.0))
    total: TotalStake = TotalStake(Currency[Token.ALPHA](0.0))


class _FileBackedBlock(Block):
    """
    Block for local development: number and hash default to placeholder values.
    """

    number: BlockNumber = BlockNumber(0)
    hash: BlockHash = BlockHash("0x" + "0" * 64)


class _FileBackedNeuron(Neuron):
    """
    Neuron for local development. Only hotkey and axon_info (ip/port) are meaningful; every other
    field defaults so the dev file stays small while still being validated by the real model.
    """

    uid: NeuronUid = NeuronUid(0)
    coldkey: Coldkey = Coldkey("")
    active: NeuronActive = NeuronActive(True)
    axon_info: _FileBackedAxonInfo
    stake: Stake = Stake(0.0)
    rank: Rank = Rank(0.0)
    emission: Emission = Emission(Currency[Token.ALPHA](0.0))
    incentive: Incentive = Incentive(0.0)
    consensus: Consensus = Consensus(0.0)
    trust: Trust = Trust(0.0)
    validator_trust: ValidatorTrust = ValidatorTrust(0.0)
    dividends: Dividends = Dividends(0.0)
    last_update: Timestamp = Timestamp(0)
    validator_permit: ValidatorPermit = ValidatorPermit(False)
    pruning_score: PruningScore = PruningScore(0)
    stakes: _FileBackedStakes = _FileBackedStakes()

    @model_validator(mode="after")
    def _default_coldkey(self) -> "_FileBackedNeuron":
        if not self.coldkey:
            self.coldkey = Coldkey(self.hotkey)
        return self


class _FileBackedNeuronsResponse(GetNeuronsResponse):
    """
    A GetNeuronsResponse for local development, parsed from a YAML/JSON file. The block and every
    neuron field except hotkey and axon_info ip/port are optional and default to placeholder values.
    """

    block: _FileBackedBlock = _FileBackedBlock()
    neurons: dict[Hotkey, _FileBackedNeuron]

    @model_validator(mode="before")
    @classmethod
    def _fill_hotkeys(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        neurons = data.get("neurons") or {}
        if not isinstance(neurons, dict):
            return data
        for hotkey, neuron in neurons.items():
            if not isinstance(neuron, dict):
                continue
            existing = neuron.get("hotkey")
            # Disallow explicit body hotkey that contradicts the dict key — almost certainly a typo.
            if existing is not None and existing != hotkey:
                raise ValueError(
                    f"file-backed neuron at key {hotkey!r} has a conflicting 'hotkey' field {existing!r};"
                    f" remove 'hotkey' from the body or make it match the dict key"
                )
            # Populate hotkey from the dict key so callers never see a missing hotkey field.
            neuron.setdefault("hotkey", hotkey)
        return data


def load_file_backed_neurons(path: str) -> GetNeuronsResponse:
    """
    Loads neurons from a local YAML (or JSON) file for local development, validating the contents
    against the real GetNeuronsResponse model. The file is a GetNeuronsResponse where everything
    except each neuron's hotkey (its key) and axon_info ip/port may be omitted and defaults applied.
    """
    data = yaml.safe_load(Path(path).read_text())
    return _FileBackedNeuronsResponse.model_validate(data)
