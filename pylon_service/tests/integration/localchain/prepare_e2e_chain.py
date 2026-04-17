"""
Local subtensor e2e tests chain state preparation script.

Starts a fresh local subtensor chain in Docker, prepares
the test state (wallets, subnets, neurons, stake), and
creates a Docker snapshot image for repeatable test runs.

Requirements:
    - docker

Chain state after preparation::

    ┌─────────────────────────────────────────────────────────────────────┐
    │ Subnet 1 (tempo 100)              │ Subnet 2 (tempo 50)            │
    ├─────────┬───────────┬─────────────┼─────────┬───────────┬──────────┤
    │ UID     │ Account   │ Role        │ UID     │ Account   │ Role     │
    ├─────────┼───────────┼─────────────┼─────────┼───────────┼──────────┤
    │ 0       │ (builtin) │ validator   │ 0       │ (builtin) │ validat. │
    │ 1       │ alice     │ validator   │ 1       │ alice     │ validat. │
    │ 2       │ bob       │ validator   │ 2       │ bob       │ validat. │
    │ 3       │ charlie   │ miner       │ 3       │ charlie   │ miner    │
    │ 4       │ dave      │ miner       │ 4       │ dave      │ miner    │
    │ 5 - 255 │ filler    │ miner       │ 5 - 255 │ filler    │ miner    │
    └─────────┴───────────┴─────────────┴─────────┴───────────┴──────────┘
    Total: 256 neurons per subnet (max capacity)

    Validators: alice & bob (10k TAO staked each, per subnet)
    Commitments: charlie & dave on subnet 1
    Filler neurons: random wallets, no stake, no commitments

Preparation steps (in order):

    1.  Start fresh localchain
    2.  Disable admin freeze window (sudo)
    3.  Transfer 100k TAO from Alice to Bob, Charlie, Dave
    4.  Create subnets 1 and 2
    5.  Register Alice, Bob, Charlie, Dave on each subnet
    6.  Enable subtokens on both subnets
    7.  Stake 10k TAO for Alice and Bob on each subnet
    8.  Set low tempo (50) on subnet 2
    9.  Set commitments for Charlie and Dave on subnet 1
    10. Create & fund 251 filler wallets
    11. Register 251 filler neurons on each subnet (parallelized)
    12. Set Drand.NextUnsignedAt (MUST be last before snapshot)
    13. Create Docker snapshot
"""

from __future__ import annotations

import asyncio
import logging
import tempfile

from bittensor_wallet import Wallet

from tests.integration.containers import LocalChainImage
from tests.integration.localchain.common import LOW_TEMPO, log_step
from tests.integration.localchain.dev_accounts import DevAccount
from tests.integration.localchain.manager import LocalChainManager

logger = logging.getLogger(__name__)

SNAPSHOT_IMAGE = LocalChainImage.PREPARED_E2E

VALIDATORS = [DevAccount.ALICE, DevAccount.BOB]
NETUIDS = [1, 2, 3]
TRANSFER_AMOUNT_TAO = 100_000
STAKE_AMOUNT_TAO = 10
LOW_TEMPO_NETUIDS = [2, 3]
MECHANISMS_NETUID = 3

MAX_NEURONS = 256
FILLER_NEURONS_NETUIDS = [1, 2]
FILLER_NEURON_COUNT = MAX_NEURONS - len(DevAccount) - 1  # 251 (UID 0 is a pre-existing node)
FILLER_TRANSFER_AMOUNT_TAO = 500
FILLER_REGISTRATION_BATCH_SIZE = 64
FILLER_TRANSFER_BATCH_SIZE = 256


def create_filler_wallets(count: int, wallet_dir: str) -> list[Wallet]:
    """
    Create filler wallets in the given directory.

    Args:
        count: Number of wallets to create.
        wallet_dir: Directory to store wallet files.

    Returns:
        List of created Wallet instances.
    """
    wallets: list[Wallet] = []
    for i in range(count):
        name = f"filler{i}"
        uri = f"//Filler{i}"
        wallet = Wallet(name=name, path=wallet_dir)
        wallet.create_coldkey_from_uri(uri, use_password=False, overwrite=True)
        wallet.create_hotkey_from_uri(uri, use_password=False, overwrite=True)
        wallets.append(wallet)
    return wallets


async def main() -> None:
    async with LocalChainManager() as manager:
        log_step("Starting fresh local chain")

        alice = DevAccount.ALICE

        log_step("Disabling admin freeze window")
        await manager.disable_admin_freeze_window()

        log_step("Transferring TAO")
        for dev in [DevAccount.BOB, DevAccount.CHARLIE, DevAccount.DAVE]:
            logger.info("Transferring %d TAO to %s (%s)", TRANSFER_AMOUNT_TAO, dev.wallet_name, dev.coldkey_ss58)
            await manager.transfer(
                wallet=alice.wallet, destination_ss58=dev.coldkey_ss58, amount_tao=TRANSFER_AMOUNT_TAO
            )

        log_step("Creating subnets")
        existing_subnets = await manager.get_total_networks()
        for netuid in NETUIDS:
            if netuid < existing_subnets:
                logger.info("Subnet %d already exists, skipping", netuid)
            else:
                logger.info("Creating subnet %d", netuid)
                await manager.register_subnet(wallet=alice.wallet)

        log_step("Registering neurons")
        for netuid in NETUIDS:
            for dev in DevAccount:
                role = "validator" if dev in VALIDATORS else "non-validator"
                logger.info("Registering %s (%s) on subnet %d", dev.wallet_name, role, netuid)
                await manager.register_neuron(wallet=dev.wallet, netuid=netuid)

        log_step("Enabling subtokens")
        for netuid in NETUIDS:
            logger.info("Enabling subtokens on subnet %d", netuid)
            await manager.enable_subtokens(netuid=netuid)

        log_step("Staking TAO for validators")
        for netuid in NETUIDS:
            for dev in VALIDATORS:
                logger.info("Staking %d TAO for %s on subnet %d", STAKE_AMOUNT_TAO, dev.wallet_name, netuid)
                await manager.add_stake(
                    wallet=dev.wallet,
                    netuid=netuid,
                    hotkey_ss58=dev.hotkey_ss58,
                    amount_tao=STAKE_AMOUNT_TAO,
                )

        for netuid in LOW_TEMPO_NETUIDS:
            log_step(f"Setting low tempo ({LOW_TEMPO}) on subnet {netuid}")
            await manager.set_tempo(netuid=netuid, tempo=LOW_TEMPO)

        await manager.setup_mechanisms(netuid=MECHANISMS_NETUID)

        log_step("Setting commitments")
        for dev in [DevAccount.CHARLIE, DevAccount.DAVE]:
            data = f"commitment-{dev.wallet_name}"
            logger.info("Setting commitment for %s: %r", dev.wallet_name, data)
            await manager.set_commitment(wallet=dev.wallet, netuid=1, data=data)
        for dev in [DevAccount.ALICE, DevAccount.BOB]:
            revealed_commitment = f"revealed-commitment-{dev.wallet_name}"
            logger.info("Setting  revealed commitment for %s: %s", dev.wallet_name, revealed_commitment)
            await manager.set_revealed_commitment(
                wallet=dev.wallet, netuid=1, data=revealed_commitment, blocks_until_reveal=1
            )
        await manager.wait_for_commitment_reveal(netuid=1, expected_count=2)

        log_step("Tuning registration parameters for bulk registration")
        for netuid in FILLER_NEURONS_NETUIDS:
            await manager.set_max_registrations_per_block(netuid=netuid, max_regs=256)
            await manager.set_target_registrations_per_interval(netuid=netuid, target=256)
            await manager.set_tx_rate_limit(netuid=netuid, rate_limit=0)

        log_step(f"Creating {FILLER_NEURON_COUNT} filler wallets")
        with tempfile.TemporaryDirectory(prefix="filler-wallets-") as tmpdir:
            filler_wallets = create_filler_wallets(FILLER_NEURON_COUNT, wallet_dir=tmpdir)
            logger.info("Created %d filler wallets in %s", len(filler_wallets), tmpdir)

            log_step(f"Funding {FILLER_NEURON_COUNT} filler wallets")
            destinations = [(w.coldkeypub.ss58_address, FILLER_TRANSFER_AMOUNT_TAO) for w in filler_wallets]
            await manager.batch_transfer(
                wallet=alice.wallet,
                destinations=destinations,
                batch_size=FILLER_TRANSFER_BATCH_SIZE,
            )

            for netuid in FILLER_NEURONS_NETUIDS:
                log_step(f"Registering {FILLER_NEURON_COUNT} filler neurons on subnet {netuid}")
                await manager.register_neurons_concurrent(
                    wallets=filler_wallets,
                    netuid=netuid,
                    batch_size=FILLER_REGISTRATION_BATCH_SIZE,
                )

        # Phase 1 of drand workaround — see localchain/README.md#drand-workaround
        log_step("Setting Drand.NextUnsignedAt")
        await manager.offset_drand_next_unsigned_at()

        log_step("Creating Docker snapshot")
        manager.make_snapshot(image_name=SNAPSHOT_IMAGE)

        log_step("Done")
        logger.info("Snapshot image: %s", SNAPSHOT_IMAGE)
        logger.info("To run manually:")
        logger.info("  docker run --rm -p 9944:9944 %s True --no-purge", SNAPSHOT_IMAGE)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    asyncio.run(main())
