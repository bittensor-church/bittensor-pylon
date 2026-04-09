from __future__ import annotations

import pytest
from websockets.exceptions import ConnectionClosed

from tests.integration.contact_resilience.helpers import (
    assert_histogram_delta,
    histogram_count,
    retry_until_failure,
    retry_until_result,
)

RESTART_RETRYABLE_EXCEPTIONS = (AttributeError, ConnectionClosed, OSError, RuntimeError)


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

    baseline = await live_contact.get_latest_block()
    assert baseline.number > 0

    resilience_chain.stop()
    await retry_until_failure(lambda: live_contact.get_latest_block(), expected=RESTART_RETRYABLE_EXCEPTIONS)

    resilience_chain.start()
    recovered = await retry_until_result(
        lambda: live_contact.get_latest_block(),
        retryable_exceptions=RESTART_RETRYABLE_EXCEPTIONS,
    )

    assert recovered.number > 0
    assert_histogram_delta(error_labels, error_before)
    assert_histogram_delta(success_labels, success_before, at_least=2)
