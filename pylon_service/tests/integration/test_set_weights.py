from unittest.mock import patch

import pytest
import pytest_asyncio
from bittensor_wallet import Wallet
from pylon_client.artanis import Hotkey, PylonClient, Weight
from pylon_client.artanis.v1 import SetWeightsResponse

from pylon_service.api._unstable.tasks import ApplyWeights
from tests.helpers import wait_until
from tests.integration.localchain.dev_accounts import DevAccount
from tests.integration.localchain.manager import LocalChainManager

TARGET_HOTKEY = Hotkey(DevAccount.BOB.hotkey_ss58)
DEFAULT_WEIGHTS_SET_RATE_LIMIT = 100


@pytest_asyncio.fixture
async def low_weights_rate_limit(localchain: LocalChainManager, wallet: Wallet):
    await localchain.set_weights_rate_limit(sudo_wallet=wallet, netuid=1, rate_limit=20)
    try:
        yield
    finally:
        await localchain.set_weights_rate_limit(sudo_wallet=wallet, netuid=1, rate_limit=DEFAULT_WEIGHTS_SET_RATE_LIMIT)


@pytest.mark.asyncio
async def test_set_weights(pylon_client: PylonClient, low_weights_rate_limit):
    response = pylon_client.v1.identity.put_weights(weights={TARGET_HOTKEY: Weight(1.0)})
    assert isinstance(response, SetWeightsResponse)
    await wait_until(lambda: not ApplyWeights.tasks_running, timeout=60.0, sleep_interval=1.0)

    with patch.object(
        ApplyWeights, "_single_attempt", wraps=ApplyWeights._single_attempt, autospec=True
    ) as mock_attempt:
        response = pylon_client.v1.identity.put_weights(weights={TARGET_HOTKEY: Weight(1.0)})
        assert isinstance(response, SetWeightsResponse)
        # The task may succeed or not (in case epoch ends) - we don't care, we only check if it retries on errors like
        # set weights rate limit exceeded.
        await wait_until(lambda: not ApplyWeights.tasks_running, timeout=60.0, sleep_interval=1.0)

    assert mock_attempt.call_count >= 2
