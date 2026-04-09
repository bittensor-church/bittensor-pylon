from __future__ import annotations

import asyncio

import pytest

from tests.integration.contact_resilience.helpers import (
    add_timeout_toxic,
    assert_histogram_delta,
    histogram_count,
    remove_toxic,
    retry_until_result,
)


@pytest.mark.asyncio
async def test_cancelled_read_does_not_poison_contact(
    proxied_contact,
    toxiproxy_handle,
):
    uri = str(proxied_contact.uri)
    cancelled_labels = {
        "operation": "get_latest_block",
        "status": "cancelled",
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

    cancelled_before = histogram_count(cancelled_labels)
    success_before = histogram_count(success_labels)

    baseline = await proxied_contact.get_latest_block()
    assert baseline.number > 0

    add_timeout_toxic(
        toxiproxy_handle.name,
        toxiproxy_handle.control_url,
        name="hang-downstream",
        toxic_type="timeout",
        stream="downstream",
        timeout_ms=30_000,
    )
    task = asyncio.create_task(proxied_contact.get_latest_block())
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(asyncio.shield(task), timeout=0.5)

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    remove_toxic(toxiproxy_handle.name, toxiproxy_handle.control_url, "hang-downstream")
    recovered = await retry_until_result(lambda: proxied_contact.get_latest_block())

    assert recovered.number > 0
    assert_histogram_delta(cancelled_labels, cancelled_before)
    assert_histogram_delta(success_labels, success_before, at_least=2)
