"""
Local subtensor contact tests chain state preparation script, see localchain/README.md#seeded-data.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from tests.integration.containers import LocalChainContainer, LocalChainImage
from tests.integration.localchain.common import LOW_TEMPO, log_step
from tests.integration.localchain.dev_accounts import SUDO_WALLET, DevAccount
from tests.integration.localchain.manager import LocalChainManager

logger = logging.getLogger(__name__)

CONTACT_SNAPSHOT_IMAGE = LocalChainImage.PREPARED_CONTACT

_VALIDATORS = [DevAccount.ALICE, DevAccount.BOB]
_TRANSFER_AMOUNT_TAO = 100_000
_STAKE_AMOUNT_TAO = 10
_CONTACT_TEST_AXON_IP = "1.1.1.1"
_CONTACT_TEST_AXON_PORT = 12345


@dataclass
class SubnetConfig:
    use_commit_reveal: bool
    use_mechanisms: bool
    save_commitments: bool = False


SUBNET_CONFIGS = [
    SubnetConfig(use_commit_reveal=False, use_mechanisms=False, save_commitments=True),
    SubnetConfig(use_commit_reveal=True, use_mechanisms=False),
    SubnetConfig(use_commit_reveal=False, use_mechanisms=True),
    SubnetConfig(use_commit_reveal=True, use_mechanisms=True),
]


async def _prepare_subnet(manager: LocalChainManager, subnet_config: SubnetConfig) -> None:
    netuid = await manager.get_total_networks()
    await manager.register_subnet(wallet=DevAccount.ALICE.wallet)
    await manager.set_tempo(netuid=netuid, tempo=LOW_TEMPO)

    if subnet_config.use_commit_reveal:
        await manager.enable_commit_reveal_weights(netuid=netuid)
    else:
        await manager.disable_commit_reveal_weights(netuid=netuid)

    if subnet_config.use_mechanisms:
        await manager.setup_mechanisms(
            netuid=netuid,
        )

    for dev in DevAccount:
        if dev != DevAccount.ALICE:
            await manager.register_neuron(wallet=dev.wallet, netuid=netuid)

    await manager.enable_subtokens(netuid=netuid)

    for dev in _VALIDATORS:
        await manager.add_stake(
            wallet=dev.wallet,
            netuid=netuid,
            hotkey_ss58=dev.hotkey_ss58,
            amount_tao=_STAKE_AMOUNT_TAO,
        )

    if not subnet_config.use_commit_reveal and not subnet_config.use_mechanisms:
        await manager.set_serving_rate_limit(netuid=netuid, rate_limit=0)
        await manager.serve_axon(
            wallet=SUDO_WALLET,
            netuid=netuid,
            ip=_CONTACT_TEST_AXON_IP,
            port=_CONTACT_TEST_AXON_PORT,
        )

    if subnet_config.save_commitments:
        await manager.set_revealed_commitment(DevAccount.ALICE.wallet, netuid, "revealed-commitment-alice", 1)
        await manager.set_commitment(DevAccount.BOB.wallet, netuid, "commitment-bob")
        await manager.set_revealed_commitment(DevAccount.CHARLIE.wallet, netuid, "revealed-commitment-charlie", 1)
        await manager.set_commitment(DevAccount.DAVE.wallet, netuid, "commitment-dave")
        await manager.wait_for_commitment_reveal(netuid, expected_count=2)


async def main() -> None:
    log_step("Pulling base localchain image")
    LocalChainContainer(image=LocalChainImage.DEFAULT).pull_image()

    async with LocalChainManager() as manager:
        log_step("Starting fresh local chain")

        log_step("Disabling admin freeze window")
        await manager.disable_admin_freeze_window()

        log_step("Transferring TAO")
        for dev in DevAccount:
            if dev == DevAccount.ALICE:
                continue
            await manager.transfer(
                wallet=DevAccount.ALICE.wallet,
                destination_ss58=dev.wallet.coldkeypub.ss58_address,
                amount_tao=_TRANSFER_AMOUNT_TAO,
            )

        log_step("Creating subnets")
        for subnet_config in SUBNET_CONFIGS:
            await _prepare_subnet(manager=manager, subnet_config=subnet_config)

        # Phase 1 of drand workaround — see localchain/README.md#drand-workaround
        log_step("Setting Drand.NextUnsignedAt")
        await manager.offset_drand_next_unsigned_at()

        manager.make_snapshot(image_name=CONTACT_SNAPSHOT_IMAGE)

    logger.info("Snapshot image: %s", CONTACT_SNAPSHOT_IMAGE)
    logger.info("To run manually:")
    logger.info("  docker run --rm -p 9944:9944 %s True --no-purge", CONTACT_SNAPSHOT_IMAGE)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    asyncio.run(main())
