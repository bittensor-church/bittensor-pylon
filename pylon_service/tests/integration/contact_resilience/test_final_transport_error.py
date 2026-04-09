from __future__ import annotations

import pytest

from pylon_service.bittensor.exceptions import BittensorTransportError
from tests.integration.contact_resilience.helpers import add_timeout_toxic, remove_toxic, retry_until_failure


@pytest.mark.asyncio
async def test_contact_raises_bittensor_transport_error_after_retry_failure(
    proxied_contact,
    toxiproxy_handle,
):
    baseline = await proxied_contact.get_latest_block()
    assert baseline.number > 0

    add_timeout_toxic(
        toxiproxy_handle.name,
        toxiproxy_handle.control_url,
        name="break-upstream",
        toxic_type="timeout",
        stream="upstream",
        timeout_ms=1,
    )
    try:
        exc = await retry_until_failure(
            lambda: proxied_contact.get_latest_block(),
            expected=BittensorTransportError,
        )
    finally:
        remove_toxic(toxiproxy_handle.name, toxiproxy_handle.control_url, "break-upstream")

    assert isinstance(exc, BittensorTransportError)
    assert exc.operation == "get_block"
    assert str(exc.uri) == str(proxied_contact.uri)
    assert exc.error_type
    assert exc.transport_gist
