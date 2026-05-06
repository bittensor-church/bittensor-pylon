import asyncio

import pytest
import pytest_asyncio
from pylon_client.artanis import Hotkey, Weight
from pylon_client.artanis.v1 import SetWeightsResponse
from pylon_commons.types import MechanismId
from turbobt.client import Bittensor

from tests.integration.localchain.dev_accounts import DevAccount
from tests.integration.localchain.manager import LocalChainManager

TARGET_HOTKEY = Hotkey(DevAccount.ALICE.hotkey_ss58)
DEFAULT_WEIGHTS_SET_RATE_LIMIT = 100


@pytest_asyncio.fixture
async def low_weights_rate_limit(localchain: LocalChainManager):
    await localchain.set_weights_rate_limit(netuid=2, rate_limit=20)
    try:
        yield
    finally:
        await localchain.set_weights_rate_limit(netuid=2, rate_limit=DEFAULT_WEIGHTS_SET_RATE_LIMIT)


@pytest.mark.asyncio
async def test_set_weights(pylon_client_factory, low_weights_rate_limit, localchain: LocalChainManager):
    with pylon_client_factory("sn2") as client:
        response = client.v1.identity.put_weights(weights={TARGET_HOTKEY: Weight(1.0)})
        assert isinstance(response, SetWeightsResponse)

        async with Bittensor(uri=localchain.ws_url) as bt:
            neurons = await asyncio.shield(bt.subnet(2).list_neurons())
            bob_uid = next(n.uid for n in neurons if n.hotkey == DevAccount.BOB.hotkey_ss58)
            alice_uid = next(n.uid for n in neurons if n.hotkey == DevAccount.ALICE.hotkey_ss58)

            async with asyncio.timeout(30):
                while True:
                    weights = await asyncio.shield(bt.subnet(2).weights.get(bob_uid))
                    if weights:
                        break
                    await asyncio.sleep(1)

            assert alice_uid in weights
            assert weights[alice_uid] == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_set_mechanism_weights(pylon_client_factory, low_weights_rate_limit, localchain: LocalChainManager):
    with pylon_client_factory("sn3") as client:
        response = client.unstable.identity.put_weights(
            weights={TARGET_HOTKEY: Weight(1.0)}, mechanism_id=MechanismId(1)
        )
        assert isinstance(response, SetWeightsResponse)

        async with Bittensor(uri=localchain.ws_url) as bt:
            neurons = await asyncio.shield(bt.subnet(3).list_neurons())
            bob_uid = next(n.uid for n in neurons if n.hotkey == DevAccount.BOB.hotkey_ss58)
            alice_uid = next(n.uid for n in neurons if n.hotkey == DevAccount.ALICE.hotkey_ss58)

            async with asyncio.timeout(30):
                while True:
                    weights = await asyncio.shield(bt.subnet(3).weights.get(bob_uid, mechanism_id=1))
                    if weights:
                        break
                    await asyncio.sleep(1)

            assert alice_uid in weights
            assert weights[alice_uid] == pytest.approx(1.0)
