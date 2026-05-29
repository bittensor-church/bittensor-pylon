import asyncio

import pytest
from pylon_commons.types import NetUid, Tempo, Weight

from pylon_service.api.epoch import get_epoch_containing_block
from tests.integration.localchain.dev_accounts import DevAccount
from tests.integration.localchain.manager import LocalChainManager


@pytest.mark.asyncio
async def test_get_weights_status(pylon_client_factory, localchain: LocalChainManager):
    with pylon_client_factory("sn2") as client:
        # wait to start of a new epoch so we get weights status in the same epoch as we set weights
        block_number = client.unstable.open_access.get_latest_block_info().number
        epoch = get_epoch_containing_block(block_number, NetUid(2), Tempo(50))
        while block_number <= epoch.end:
            await asyncio.sleep(1)
            block_number = client.unstable.open_access.get_latest_block_info().number

        client.unstable.identity.put_weights(weights={DevAccount.BOB.hotkey_ss58: Weight(1.0)})

        response = client.unstable.identity.get_weights_status(block_number)

        assert response.weights_submitted
