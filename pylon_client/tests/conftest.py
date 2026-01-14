import pytest
import respx
from polyfactory.pytest_plugin import register_fixture

from tests.factories import BlockFactory, NeuronFactory


@pytest.fixture
def test_url():
    return "http://testserver:8080"


@pytest.fixture
def service_mock(test_url):
    with respx.mock(base_url=test_url) as respx_mock:
        yield respx_mock


register_fixture(BlockFactory)
register_fixture(NeuronFactory)
