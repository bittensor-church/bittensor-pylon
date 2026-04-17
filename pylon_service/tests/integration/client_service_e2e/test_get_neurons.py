import pytest
import pytest_asyncio
from pylon_client.artanis import BlockNumber, Hotkey, NetUid, PylonClient, PylonNotFound
from pylon_client.artanis.v1 import GetNeuronsResponse

from tests.integration.localchain.dev_accounts import DevAccount
from tests.integration.localchain.manager import LocalChainManager

STAKE_AMOUNT_TAO = 1


@pytest_asyncio.fixture
async def added_stake(localchain: LocalChainManager, pylon_client: PylonClient):
    pre_response = pylon_client.v1.open_access.get_latest_neurons(netuid=NetUid(1))
    saved_block = pre_response.block.number
    saved_neurons = pre_response.neurons

    bob = DevAccount.BOB
    await localchain.add_stake(wallet=bob.wallet, netuid=1, hotkey_ss58=bob.hotkey_ss58, amount_tao=STAKE_AMOUNT_TAO)

    try:
        yield saved_block, saved_neurons
    finally:
        await localchain.remove_stake(
            wallet=bob.wallet, netuid=1, hotkey_ss58=bob.hotkey_ss58, amount_tao=STAKE_AMOUNT_TAO
        )


@pytest.mark.asyncio
async def test_get_neurons_at_specific_block(pylon_client: PylonClient, added_stake):
    saved_block, saved_neurons = added_stake
    bob_hotkey = Hotkey(DevAccount.BOB.hotkey_ss58)

    historical = pylon_client.v1.open_access.get_neurons(netuid=NetUid(1), block_number=BlockNumber(saved_block))
    latest = pylon_client.v1.open_access.get_latest_neurons(netuid=NetUid(1))

    assert isinstance(historical, GetNeuronsResponse)
    assert historical.block.number == saved_block
    assert historical.neurons == saved_neurons

    assert isinstance(latest, GetNeuronsResponse)
    # I assume that we are running chain in fast mode so we don't need to wait or check for block to pass.
    assert latest.block.number > saved_block
    assert latest.neurons[bob_hotkey].stakes.total > historical.neurons[bob_hotkey].stakes.total


def test_get_neurons_nonexistent_block(pylon_client: PylonClient):
    with pytest.raises(PylonNotFound):
        pylon_client.v1.open_access.get_neurons(netuid=NetUid(1), block_number=BlockNumber(999_999_999))
