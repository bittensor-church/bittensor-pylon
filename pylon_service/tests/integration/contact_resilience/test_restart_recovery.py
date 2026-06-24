from __future__ import annotations

import contextlib
import logging
from typing import Any, cast

import pytest
from websockets.exceptions import ConnectionClosed

from pylon_service.bittensor.exceptions import BittensorTransportError
from tests.integration.contact_resilience.helpers import (
    assert_histogram_delta,
    histogram_count,
    retry_until_failure,
    retry_until_result,
)

RESTART_RETRYABLE_EXCEPTIONS = (AttributeError, BittensorTransportError, ConnectionClosed, OSError, RuntimeError)


class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@contextlib.contextmanager
def capture_contact_logs():
    contact_logger = logging.getLogger("pylon_service.bittensor.contact")
    handler = _ListHandler()
    previous_level = contact_logger.level
    contact_logger.addHandler(handler)
    contact_logger.setLevel(logging.INFO)
    try:
        yield handler.records
    finally:
        contact_logger.removeHandler(handler)
        contact_logger.setLevel(previous_level)


@pytest.mark.asyncio
async def test_contact_recovers_after_subtensor_restart(
    resilience_chain,
    live_contact,
):
    uri = str(live_contact.uri)
    error_labels = {
        "operation": "get_latest_block",
        "status": "error",
        "uri": uri,
        "netuid": "N/A",
        "hotkey": "N/A",
    }
    success_labels = {
        "operation": "get_latest_block",
        "status": "success",
        "uri": uri,
        "netuid": "N/A",
        "hotkey": "N/A",
    }

    success_before = histogram_count(success_labels)
    error_before = histogram_count(error_labels)

    with capture_contact_logs() as records:
        baseline = await live_contact.get_latest_block()
        assert baseline.number > 0

        await resilience_chain.stop()
        await retry_until_failure(lambda: live_contact.get_latest_block(), expected=RESTART_RETRYABLE_EXCEPTIONS)

        await resilience_chain.start()
        recovered = await retry_until_result(
            lambda: live_contact.get_latest_block(),
            retryable_exceptions=RESTART_RETRYABLE_EXCEPTIONS,
        )

    assert recovered.number > 0
    assert any(cast(dict[str, Any], record.msg)["event"] == "recreating_bittensor_contact" for record in records)
    assert all(record.exc_info is None for record in records)
    assert_histogram_delta(error_labels, error_before)
    assert_histogram_delta(success_labels, success_before, at_least=2)
