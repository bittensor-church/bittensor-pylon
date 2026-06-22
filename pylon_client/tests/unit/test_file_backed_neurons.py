import textwrap
from ipaddress import ip_address

import pytest
from pydantic import ValidationError

from pylon_client._internal.file_backed_neurons import (
    _FileBackedAxonInfo,
    _FileBackedNeuron,
    _FileBackedNeuronsResponse,
    load_file_backed_neurons,
)
from pylon_client._internal.pylon_commons.types import BlockHash, BlockNumber, Hotkey, NeuronUid, Port


def test_minimal_yaml(tmp_path):
    """
    A file with only the dict key and axon_info ip/port is valid; all other fields default.
    """
    path = tmp_path / "neurons.yaml"
    path.write_text(
        textwrap.dedent("""\
        neurons:
          5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY:
            axon_info:
              ip: 127.0.0.1
              port: 8091
    """)
    )

    response = load_file_backed_neurons(str(path))

    hotkey = Hotkey("5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY")
    expected = _FileBackedNeuronsResponse(
        neurons={
            hotkey: _FileBackedNeuron(
                hotkey=hotkey,
                axon_info=_FileBackedAxonInfo(ip=ip_address("127.0.0.1"), port=Port(8091)),
            )
        }
    )
    assert response == expected


def test_overriding_defaults(tmp_path):
    """
    Block fields and optional neuron fields specified in the file override the model defaults.
    """
    path = tmp_path / "neurons.yaml"
    path.write_text(
        textwrap.dedent("""\
        block:
          number: 123
          hash: "0xabcd1234"
        neurons:
          5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY:
            uid: 7
            axon_info:
              ip: 127.0.0.1
              port: 8091
    """)
    )

    response = load_file_backed_neurons(str(path))

    hotkey = Hotkey("5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY")
    assert response.block.number == BlockNumber(123)
    assert response.block.hash == BlockHash("0xabcd1234")
    assert response.neurons[hotkey].uid == NeuronUid(7)


def test_incompatible_hotkeys(tmp_path):
    """
    When the dict key and the explicit hotkey field in the neuron body disagree, a ValidationError
    is raised. The dict key is the sole source of truth for the hotkey.
    """
    path = tmp_path / "neurons.yaml"
    path.write_text(
        textwrap.dedent("""\
        neurons:
          hotkey_a:
            hotkey: hotkey_b
            axon_info:
              ip: 127.0.0.1
              port: 8091
    """)
    )

    with pytest.raises(ValidationError, match="conflicting 'hotkey' field"):
        load_file_backed_neurons(str(path))
