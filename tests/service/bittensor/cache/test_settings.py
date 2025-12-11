"""
Tests for cache settings.
"""

import pytest

from pylon.service.bittensor.cache.settings import CacheSettings


@pytest.mark.parametrize(
    ("soft_limit", "hard_limit", "expected"),
    (
        ("100", "200", 1080.0),
        ("150", "200", 1080.0),
        ("150", "350", 1680.0),
        ("1", "2", 12.0),
        ("5", "7", 12.0),
    ),
)
def test_recent_neurons_update_task_interval(monkeypatch, soft_limit, hard_limit, expected):
    monkeypatch.setenv("PYLON_RECENT_NEURONS_SOFT_LIMIT", soft_limit)
    monkeypatch.setenv("PYLON_RECENT_NEURONS_HARD_LIMIT", hard_limit)
    settings = CacheSettings()
    assert settings.recent_neurons_update_task_interval == expected
