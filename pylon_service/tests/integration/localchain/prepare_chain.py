"""
Local subtensor chain state preparation script.

Starts a fresh local subtensor chain in Docker, prepares
the test state (wallets, subnets, neurons, stake), and
creates a Docker snapshot image for repeatable test runs.

Requirements:
    - docker

Neuron layout (identical on both subnets):
    Validator 1:     alice   (//Alice) — subnet owner, pre-funded on localnet
    Validator 2:     bob     (//Bob)
    Non-validator 1: charlie (//Charlie)
    Non-validator 2: dave    (//Dave)

Subnet configuration:
    Subnet 1: default tempo (100)
    Subnet 2: low tempo (50) — for fast commit-reveal weight tests
"""

from __future__ import annotations

import asyncio
import logging

from tests.integration.containers import LocalChainImage
from tests.integration.localchain.dev_accounts import DevAccount
from tests.integration.localchain.manager import LocalChainManager

logger = logging.getLogger(__name__)

SNAPSHOT_IMAGE = LocalChainImage.PREPARED

VALIDATORS = [DevAccount.ALICE, DevAccount.BOB]
NETUIDS = [1, 2]
TRANSFER_AMOUNT_TAO = 100_000
STAKE_AMOUNT_TAO = 10_000
LOW_TEMPO_NETUID = 2
LOW_TEMPO = 50
DRAND_WORKER_MARGIN = 80  # Roughly after how many blocks after starting the chain drand rounds will start fetching


def log_step(message: str) -> None:
    print(f"\n{'=' * 40}")
    print(f"  {message}")
    print(f"{'=' * 40}\n")


async def main() -> None:
    async with LocalChainManager() as manager:
        log_step("Starting fresh local chain")

        alice = DevAccount.ALICE

        log_step("Disabling admin freeze window")
        await manager.disable_admin_freeze_window(sudo_wallet=alice.wallet)

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
            await manager.enable_subtokens(sudo_wallet=alice.wallet, netuid=netuid)

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

        log_step(f"Setting low tempo ({LOW_TEMPO}) on subnet {LOW_TEMPO_NETUID}")
        await manager.set_tempo(sudo_wallet=alice.wallet, netuid=LOW_TEMPO_NETUID, tempo=LOW_TEMPO)

        log_step("Setting commitments")
        for dev in [DevAccount.CHARLIE, DevAccount.DAVE]:
            data = f"commitment-{dev.wallet_name}"
            logger.info("Setting commitment for %s: %r", dev.wallet_name, data)
            await manager.set_commitment(wallet=dev.wallet, netuid=1, data=data)

        # Phase 1 of drand workaround — see localchain/README.md#drand-workaround
        log_step("Setting Drand.NextUnsignedAt")
        current_block = await manager.get_current_block_number()
        await manager.set_drand_next_unsigned_at(
            sudo_wallet=alice.wallet, block_number=current_block + DRAND_WORKER_MARGIN
        )

        log_step("Creating Docker snapshot")
        manager.make_snapshot(image_name=SNAPSHOT_IMAGE)

        log_step("Done")
        logger.info("Snapshot image: %s", SNAPSHOT_IMAGE)
        logger.info("To run manually:")
        logger.info("  docker run --rm -p 9944:9944 %s", SNAPSHOT_IMAGE)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    asyncio.run(main())
