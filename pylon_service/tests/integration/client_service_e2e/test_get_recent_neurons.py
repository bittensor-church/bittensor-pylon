import time

import pytest
from pylon_client.artanis import NetUid, PylonResponseException
from pylon_client.artanis.v1 import GetNeuronsResponse


def test_get_recent_neurons_after_cache_ready(pylon_client_factory):
    with pylon_client_factory("sn1") as client:
        # If the test is first in the test session, we need to try multiple times until the background task fetches
        # recent objects.
        deadline = time.monotonic() + 20.0
        while True:
            try:
                response = client.v1.open_access.get_recent_neurons(netuid=NetUid(1))
                break
            except PylonResponseException:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(1.0)

        assert isinstance(response, GetNeuronsResponse)
        assert response.block.number > 0
        assert response.block.hash
        assert len(response.neurons) > 0


def test_get_recent_neurons_for_uncached_subnet(pylon_client_factory):
    with pylon_client_factory("sn1") as client:
        with pytest.raises(PylonResponseException) as exc_info:
            client.v1.open_access.get_recent_neurons(netuid=NetUid(99))

        assert exc_info.value.status_code == 503
