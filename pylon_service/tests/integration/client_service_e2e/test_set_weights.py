import asyncio

import pytest
import pytest_asyncio
import structlog
from pylon_client.artanis import Hotkey, Weight
from pylon_client.artanis.v1 import SetWeightsResponse
from pylon_commons.types import BlockNumber, MechanismId, NetUid, Tempo
from turbobt.client import Bittensor

from pylon_service.api.epoch import get_epoch_containing_block
from tests.helpers import wait_until
from tests.integration.localchain.dev_accounts import DevAccount
from tests.integration.localchain.manager import LocalChainManager
from tests.integration.mitmproxy import CommitTimelockedMechanismWeightsFrame, WSFrame

logger = structlog.stdlib.get_logger(__name__)

_CHARLIE_HOTKEY_PUBLIC_KEY = DevAccount.CHARLIE.wallet.hotkey.public_key
assert _CHARLIE_HOTKEY_PUBLIC_KEY is not None

TARGET_HOTKEY = Hotkey(DevAccount.ALICE.hotkey_ss58)
SUBMITTER_ADDRESS = f"0x{_CHARLIE_HOTKEY_PUBLIC_KEY.hex()}"
DEFAULT_WEIGHTS_SET_RATE_LIMIT = 100

NETUID_AFTER_REGISTRATION = 4
IDENTITY_AFTER_REGISTRATION = "sn4"
TEMPO_AFTER_REGISTRATION = 50
MIN_REMAINING_BLOCKS = 40


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


async def _wait_for_epoch_start(bt: Bittensor, timeout: float = 60.0) -> None:
    async with asyncio.timeout(timeout):
        while True:
            head = await bt.head.get()
            assert head.number is not None
            block_number = BlockNumber(head.number)
            epoch = get_epoch_containing_block(
                block_number, NetUid(NETUID_AFTER_REGISTRATION), Tempo(TEMPO_AFTER_REGISTRATION)
            )
            if epoch.end - block_number >= MIN_REMAINING_BLOCKS:
                return
            await asyncio.sleep(0.5)


@pytest_asyncio.fixture
async def extrinsic_decoder(localchain: LocalChainManager):
    yield await localchain.get_extrinsic_decoder()


# Loop scope session is needed to use localchain fixture that uses the same loop scope.
@pytest.mark.asyncio(loop_scope="session")
async def test_set_weights_succeeds_after_registration(
    pylon_client_factory, localchain: LocalChainManager, ws_recorder, extrinsic_decoder
):
    charlie = DevAccount.CHARLIE.wallet

    def is_expected_submit(frame: WSFrame) -> bool:
        decoded = CommitTimelockedMechanismWeightsFrame.from_ws_frame(frame, extrinsic_decoder)
        return (
            decoded is not None
            and decoded.address == SUBMITTER_ADDRESS
            and decoded.call_args.netuid == NETUID_AFTER_REGISTRATION
        )

    logger.info("waiting_for_epoch_with_enough_remaining_blocks", netuid=NETUID_AFTER_REGISTRATION)
    async with Bittensor(uri=localchain.ws_url) as bt:
        await _wait_for_epoch_start(bt)

    logger.info("starting_pylon_client", identity_name=IDENTITY_AFTER_REGISTRATION)
    with pylon_client_factory(IDENTITY_AFTER_REGISTRATION) as client:
        logger.info("submitting_weights_for_unregistered_target", hotkey=TARGET_HOTKEY)
        response = client.v1.identity.put_weights(weights={TARGET_HOTKEY: Weight(1.0)})
        assert isinstance(response, SetWeightsResponse)

        logger.info("waiting_for_first_set_weights_submit")
        await wait_until(
            lambda: any(is_expected_submit(f) for f in ws_recorder.frames),
            timeout=10,
        )

        logger.info("registering_charlie", netuid=NETUID_AFTER_REGISTRATION)
        await localchain.register_neuron(wallet=charlie, netuid=NETUID_AFTER_REGISTRATION)
        logger.info("adding_stake_for_charlie", netuid=NETUID_AFTER_REGISTRATION)
        await localchain.add_stake(
            wallet=charlie,
            netuid=NETUID_AFTER_REGISTRATION,
            hotkey_ss58=charlie.hotkey.ss58_address,
            amount_tao=10_000,
        )

        async with Bittensor(uri=localchain.ws_url) as bt:
            logger.info("fetching_neurons_to_resolve_uids")
            neurons = await asyncio.shield(bt.subnet(NETUID_AFTER_REGISTRATION).list_neurons())
            charlie_uid = next(n.uid for n in neurons if n.hotkey == charlie.hotkey.ss58_address)
            alice_uid = next(n.uid for n in neurons if n.hotkey == DevAccount.ALICE.hotkey_ss58)
            logger.info("resolved_uids", charlie_uid=charlie_uid, alice_uid=alice_uid)

            logger.info("waiting_for_weights_on_chain", timeout_seconds=60)
            async with asyncio.timeout(60):
                while True:
                    weights = await asyncio.shield(bt.subnet(NETUID_AFTER_REGISTRATION).weights.get(charlie_uid))
                    if weights:
                        break
                    await asyncio.sleep(1)

            logger.info("weights_observed_on_chain", weights=weights)
            assert alice_uid in weights
            assert weights[alice_uid] == pytest.approx(1.0)

    submit_frames = [f for f in ws_recorder.frames if is_expected_submit(f)]
    assert len(submit_frames) >= 2, (
        "Expected the pylon service to retry the setWeights extrinsic at least once "
        "(first attempt fails because the submitting hotkey is not registered yet, the second "
        f"succeeds after registration), but only {len(submit_frames)} submit attempts were "
        f"recorded."
    )
