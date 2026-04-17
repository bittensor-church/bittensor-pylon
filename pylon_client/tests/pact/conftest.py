from pathlib import Path

import pytest

from tests.pact.constants import HOTKEY_1, HOTKEY_2
from tests.pact.matchers import (
    commitment_response_matcher,
    commitments_response_matcher,
    extrinsic_response_matcher,
    latest_block_info_response_matcher,
    neurons_response_matcher,
    revealed_commitments_response_matcher,
    set_commitment_response_matcher,
    set_revealed_commitment_response_matcher,
    set_weights_response_matcher,
    single_revealed_commitment_response_matcher,
    v1_commitments_response_matcher,
    validators_response_matcher,
)

PACTS_DIR = Path(__file__).parent / "pacts"


@pytest.fixture(scope="session")
def pacts_dir() -> Path:
    PACTS_DIR.mkdir(parents=True, exist_ok=True)
    return PACTS_DIR


@pytest.fixture
def get_neurons_response_matcher() -> dict:
    return neurons_response_matcher(HOTKEY_1, HOTKEY_2)


@pytest.fixture
def get_validators_response_matcher() -> dict:
    return validators_response_matcher(HOTKEY_1, HOTKEY_2)


@pytest.fixture
def get_commitment_response_matcher() -> dict:
    return commitment_response_matcher(HOTKEY_1)


@pytest.fixture
def get_commitments_response_matcher() -> dict:
    return commitments_response_matcher(HOTKEY_1, HOTKEY_2)


@pytest.fixture
def get_commitments_v1_response_matcher() -> dict:
    return v1_commitments_response_matcher(HOTKEY_1, HOTKEY_2)


@pytest.fixture
def get_extrinsic_response_matcher() -> dict:
    return extrinsic_response_matcher()


@pytest.fixture
def put_weights_response_matcher() -> dict:
    return set_weights_response_matcher()


@pytest.fixture
def post_commitment_response_matcher() -> dict:
    return set_commitment_response_matcher()


@pytest.fixture
def post_revealed_commitment_response_matcher() -> dict:
    return set_revealed_commitment_response_matcher()


@pytest.fixture
def get_revealed_commitments_response_matcher() -> dict:
    return revealed_commitments_response_matcher(HOTKEY_1, HOTKEY_2)


@pytest.fixture
def get_own_revealed_commitments_response_matcher() -> dict:
    return single_revealed_commitment_response_matcher(HOTKEY_1)


@pytest.fixture
def get_latest_block_info_response_matcher() -> dict:
    return latest_block_info_response_matcher()
