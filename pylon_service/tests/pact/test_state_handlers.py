import inspect
from unittest.mock import Mock

from pylon_service.api._unstable.tasks import ApplyWeights
from tests.pact.state_handlers import WeightsCanBeSetHandler


def test_weights_can_be_set_handler_patches_schedule_with_sync_mock(monkeypatch):
    handler = WeightsCanBeSetHandler(Mock(), Mock(), Mock(), {}, monkeypatch)

    handler.setup({})

    assert isinstance(ApplyWeights.schedule, Mock)
    assert not inspect.iscoroutinefunction(ApplyWeights.schedule)
