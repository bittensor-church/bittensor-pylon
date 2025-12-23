import pytest
from bittensor_wallet import Wallet
from polyfactory.pytest_plugin import register_fixture

from tests.behave import Behave
from tests.factories import BlockFactory, NeuronFactory


@pytest.fixture
def wallet():
    return Wallet(path="tests/wallets", name="pylon", hotkey="pylon")


@pytest.fixture
def behave() -> Behave:
    return Behave()


register_fixture(BlockFactory)
register_fixture(NeuronFactory)
