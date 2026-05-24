from ipaddress import ip_address
from pathlib import Path

import yaml

from pylon_client._internal.pylon_commons.types import Hotkey, Port
from pylon_client._internal.file_backed_neurons import _FileBackedAxonInfo, _FileBackedNeuron, _FileBackedNeuronsResponse


def build_file_backed_neurons(neurons: dict[str, tuple[str, int]]) -> _FileBackedNeuronsResponse:
    """
    Builds a _FileBackedNeuronsResponse from a {hotkey: (ip, port)} mapping, relying on the file-backed
    model defaults for every other field.
    """
    return _FileBackedNeuronsResponse(
        neurons={
            Hotkey(hotkey): _FileBackedNeuron(
                hotkey=Hotkey(hotkey),
                axon_info=_FileBackedAxonInfo(ip=ip_address(ip), port=Port(port)),
            )
            for hotkey, (ip, port) in neurons.items()
        }
    )


def write_neurons_file(path: Path, neurons: dict[str, tuple[str, int]]) -> _FileBackedNeuronsResponse:
    """
    Builds a file-backed neurons response from {hotkey: (ip, port)}, serializes it to YAML at `path`, and
    returns the constructed response so tests can assert equality against the loaded result.
    """
    expected = build_file_backed_neurons(neurons)
    path.write_text(yaml.safe_dump(expected.model_dump(mode="json")))
    return expected
