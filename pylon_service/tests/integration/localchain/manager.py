from __future__ import annotations

import asyncio
import enum
import itertools
import json
import logging
import subprocess
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from types import TracebackType
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urlparse

import bittensor_drand
import docker
import scalecodec
from bittensor_wallet import Wallet
from eth_account.messages import encode_defunct
from eth_account.signers.local import LocalAccount
from eth_utils.crypto import keccak
from scalecodec.utils.ss58 import ss58_decode
from turbobt.batch import Transaction
from turbobt.client import Bittensor
from turbobt.subtensor.exceptions import HotKeyAlreadyRegisteredInSubNet

from tests.integration.containers import LocalChainContainer, LocalChainImage
from tests.integration.localchain.dev_accounts import SUDO_WALLET
from tests.integration.mitmproxy import ExtrinsicDecoder

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from docker.models.containers import Container

_HOST = "localhost"
_CONTACT_TEST_AXON_IP = "1.1.1.1"
_CONTACT_TEST_AXON_PORT = 12345

_RAO_PER_TAO = 1_000_000_000

_DRAND_WORKER_MARGIN = 600  # Blocks the worker stays idle after container start, so phase 2 can pin before it wakes
_DRAND_MAX_ACCEPTABLE_GAP = (
    60  # How many rounds the worker may lag behind the current real drand round to count as synced
)
_DRAND_SYNC_MAX_ATTEMPTS = 90  # Per-phase polling cap (seconds) while synchronizing the drand worker
_DRAND_SYNC_HOLD_MARGIN = 600  # Blocks to keep the worker asleep while phase 2 pins the current round
_DRAND_WAKE_DELAY = 5  # Blocks after pinning before the worker is woken to resume fetching


class ChainStorage(enum.StrEnum):
    ADMIN_FREEZE_WINDOW = "SubtensorModule.AdminFreezeWindow"
    COMMIT_REVEAL_WEIGHTS_ENABLED = "SubtensorModule.CommitRevealWeightsEnabled"
    DRAND_LAST_STORED_ROUND = "Drand.LastStoredRound"
    DRAND_NEXT_UNSIGNED_AT = "Drand.NextUnsignedAt"
    DRAND_OLDEST_STORED_ROUND = "Drand.OldestStoredRound"
    MECHANISM_COUNT_CURRENT = "SubtensorModule.MechanismCountCurrent"
    SERVING_RATE_LIMIT = "SubtensorModule.ServingRateLimit"
    SUBTOKEN_ENABLED = "SubtensorModule.SubtokenEnabled"
    TOTAL_NETWORKS = "SubtensorModule.TotalNetworks"
    MAX_REGISTRATIONS_PER_BLOCK = "SubtensorModule.MaxRegistrationsPerBlock"
    TARGET_REGISTRATIONS_PER_INTERVAL = "SubtensorModule.TargetRegistrationsPerInterval"
    TX_RATE_LIMIT = "SubtensorModule.TxRateLimit"


@dataclass(frozen=True)
class DockerContextEndpoint:
    scheme: str
    raw_host: str
    hostname: str | None
    username: str | None
    port: int | None


class LocalChainManager:
    """
    Wrapper around a LocalChainContainer that manages its lifecycle
    and provides chain operation methods via the turbobt library.

    The container is configured externally (image, network, env vars)
    before being passed to the manager. The manager is responsible for
    starting and stopping the container.
    """

    def __init__(self, container: LocalChainContainer | None = None) -> None:
        self._container = container if container is not None else LocalChainContainer(image=LocalChainImage.DEFAULT)
        self._bt_client: Bittensor | None = None

    async def __aenter__(self) -> LocalChainManager:
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.stop()

    @property
    def container(self) -> LocalChainContainer:
        """Return the underlying LocalChainContainer."""
        return self._container

    @property
    def ws_url(self) -> str:
        return self._container.ws_url

    @property
    def http_url(self) -> str:
        return self._container.http_url

    @property
    def internal_ws_url(self) -> str:
        return self._container.internal_ws_url

    @property
    def internal_http_url(self) -> str:
        return self._container.internal_http_url

    # ---- Docker lifecycle ----

    async def start(self) -> None:
        """
        Start the underlying container and wait until it's ready.

        Raises:
            docker.errors.ImageNotFound: If the container image does not exist.
        """
        self._container.start()

    async def stop(self) -> None:
        """Stop and remove the underlying container, closing the turbobt client first."""
        self._container.stop()
        await self.close_turbobt_client()

    async def close_turbobt_client(self) -> None:
        """Close the shared turbobt client if open."""
        if self._bt_client is not None:
            await self._bt_client.__aexit__(None, None, None)
            self._bt_client = None

    @classmethod
    def load_active_docker_context(cls) -> DockerContextEndpoint:
        """Return the active Docker context endpoint."""
        return cls._load_active_docker_context()

    @staticmethod
    def resolve_rpc_host_for_context(endpoint: DockerContextEndpoint) -> str:
        """Return the RPC host for the given Docker context endpoint."""
        return LocalChainManager._resolve_rpc_host(endpoint)

    @staticmethod
    def docker_client_for_context(endpoint: DockerContextEndpoint) -> docker.DockerClient:
        """Create a Docker client for the given Docker context endpoint."""
        return LocalChainManager._create_docker_client(endpoint)

    @staticmethod
    def get_container_ip(container: Container) -> str:
        """Return the container IP address in its connected Docker network.

        Raises:
            RuntimeError: If the container has no readable IP address.
        """
        container.reload()
        network_settings = container.attrs.get("NetworkSettings", {})
        if ip_address := network_settings.get("IPAddress"):
            return ip_address

        networks = network_settings.get("Networks", {})
        for network in networks.values():
            if ip_address := network.get("IPAddress"):
                return ip_address
        raise RuntimeError("Could not determine container IP address")

    def get_container(self) -> Container:
        """Return the running Docker SDK container.

        Raises:
            RuntimeError: If the container has not been started yet.
        """
        wrapped = self._container.get_wrapped_container()
        if wrapped is None:
            raise RuntimeError("Container has not been started yet")
        return wrapped

    def is_running(self) -> bool:
        """Report whether the managed container currently exists and is running."""
        wrapped = self._container.get_wrapped_container()
        if wrapped is None:
            return False
        wrapped.reload()
        return wrapped.status == "running"

    def make_snapshot(self, image_name: str) -> None:
        """
        Commit the running container as a Docker image.

        The resulting image has CMD ["True", "--no-purge"] baked in,
        so it preserves chain state by default when started without
        an explicit command override.

        Args:
            image_name: Name (and optional tag) for the snapshot image.

        Raises:
            RuntimeError: If the container has not been started yet.
            docker.errors.APIError: If the Docker commit operation fails.
        """
        wrapped = self._container.get_wrapped_container()
        if wrapped is None:
            raise RuntimeError("Container has not been started; cannot make snapshot")
        logger.info("Creating snapshot image %s", image_name)
        repository, _, tag = image_name.partition(":")
        wrapped.commit(repository=repository, tag=tag or None, conf={"Cmd": ["True", "--no-purge"]})
        logger.info("Snapshot image %s created", image_name)

    # ---- Wallet operations (sync) ----

    @staticmethod
    def create_wallet(name: str, uri: str) -> Wallet:
        """
        Create a wallet with coldkey and hotkey derived from a seed URI.

        Args:
            name: Wallet name (e.g., "alice").
            uri: Derivation URI (e.g., "//Alice").

        Returns:
            The created Wallet instance.
        """
        logger.info("Creating wallet %s", name)
        wallet = Wallet(name=name)
        wallet.create_coldkey_from_uri(uri, use_password=False, overwrite=True)
        wallet.create_hotkey_from_uri(uri, use_password=False, overwrite=True)
        return wallet

    # ---- Chain operations (async, use turbobt) ----

    async def disable_admin_freeze_window(self) -> None:
        """
        Set AdminFreezeWindow to 0 via sudo set_storage call.

        On a fresh localnet the default AdminFreezeWindow is 10 blocks,
        which can cause sudo calls to silently fail. Setting it to 0
        eliminates this problem for all subsequent sudo operations.

        Raises:
            RuntimeError: If AdminFreezeWindow is not 0 after the call.
        """
        logger.info("Disabling AdminFreezeWindow")
        async with self._turbobt_client() as client:
            await client.subtensor._init_runtime()
            assert client.subtensor._metadata is not None
            pallet = client.subtensor._metadata.get_metadata_pallet("SubtensorModule")
            storage_function = pallet.get_storage_function("AdminFreezeWindow")
            storage_key = client.subtensor.state._storage_key(pallet, storage_function, [])

            result = await client.subtensor.sudo.sudo(
                "System",
                "set_storage",
                {"items": [[storage_key, "0x0000"]]},
                wallet=SUDO_WALLET,
            )
            await result.wait_for_finalization()

            value = await client.subtensor.state.getStorage(ChainStorage.ADMIN_FREEZE_WINDOW)
            if value != 0:
                raise RuntimeError(f"AdminFreezeWindow is {value} after sudo call, expected 0")
        logger.info("AdminFreezeWindow disabled successfully")

    async def transfer(self, wallet: Wallet, destination_ss58: str, amount_tao: int) -> None:
        """
        Transfer TAO from one account to another.

        Args:
            wallet: Source wallet.
            destination_ss58: SS58 address of the destination account.
            amount_tao: Amount to transfer in TAO.
        """
        logger.info("Transferring %d TAO to %s", amount_tao, destination_ss58)
        async with self._turbobt_client() as client:
            result = await client.subtensor.author.submitAndWatchExtrinsic(
                "Balances",
                "transfer_keep_alive",
                {"dest": destination_ss58, "value": amount_tao * _RAO_PER_TAO},
                key=wallet.coldkey,
            )
            await result.wait_for_finalization()

    async def register_subnet(self, wallet: Wallet) -> None:
        """
        Register a new subnet. Subnets are assigned sequential netuids starting from 1.

        Args:
            wallet: Wallet to register the subnet with (becomes subnet owner).
        """
        logger.info("Registering new subnet")
        async with self._turbobt_client() as client:
            await client.subnets.register(wallet=wallet)

    async def register_neuron(self, wallet: Wallet, netuid: int) -> None:
        """
        Register a neuron on a subnet via burned registration.

        Args:
            wallet: Wallet for the neuron to register.
            netuid: Subnet UID to register on.
        """
        logger.info("Registering neuron %s on subnet %d", wallet.hotkey.ss58_address, netuid)
        async with self._turbobt_client() as client:
            try:
                await client.subnet(netuid).neurons.register(wallet.hotkey, wallet=wallet)
            except HotKeyAlreadyRegisteredInSubNet:
                logger.info("Hotkey %s already registered on subnet %d, skipping", wallet.hotkey.ss58_address, netuid)

    async def enable_subtokens(self, netuid: int) -> None:
        """
        Enable subtokens on a subnet via sudo call.

        The localnet image has SubtokenEnabled=False by default, which
        blocks staking. Requires AdminFreezeWindow=0 to avoid silent failures.

        Args:
            netuid: Subnet UID to enable subtokens for.

        Raises:
            RuntimeError: If SubtokenEnabled is still False after the call.
        """
        logger.info("Enabling subtokens on subnet %d", netuid)
        async with self._turbobt_client() as client:
            result = await client.subtensor.sudo.sudo(
                "AdminUtils",
                "sudo_set_subtoken_enabled",
                {"netuid": netuid, "subtoken_enabled": True},
                wallet=SUDO_WALLET,
            )
            await result.wait_for_finalization()

            value = await client.subtensor.state.getStorage(ChainStorage.SUBTOKEN_ENABLED, netuid)
            if not bool(value):
                raise RuntimeError(
                    f"SubtokenEnabled is still False for subnet {netuid} after sudo call. "
                    "The inner sudo call likely failed silently."
                )
        logger.info("Subtokens enabled on subnet %d", netuid)

    async def enable_commit_reveal_weights(self, netuid: int) -> None:
        """
        Enable commit-reveal weights on a subnet via the admin hyperparameter extrinsic.

        Args:
            netuid: Subnet UID to enable commit-reveal weights for.

        Raises:
            RuntimeError: If commit-reveal weights are still disabled after the update.
        """
        logger.info("Enabling commit-reveal weights on subnet %d", netuid)
        async with self._turbobt_client() as client:
            result = await client.subtensor.admin_utils.sudo_set_commit_reveal_weights_enabled(
                netuid=netuid,
                enabled=True,
                wallet=SUDO_WALLET,
            )
            await result.wait_for_finalization()
        value = await self.get_storage(ChainStorage.COMMIT_REVEAL_WEIGHTS_ENABLED, netuid)
        if not bool(value):
            raise RuntimeError(f"CommitRevealWeightsEnabled is still False for subnet {netuid} after sudo call.")
        logger.info("Commit-reveal weights enabled on subnet %d", netuid)

    async def disable_commit_reveal_weights(self, netuid: int) -> None:
        """
        Disable commit-reveal weights on a subnet via the admin hyperparameter extrinsic.

        Args:
            netuid: Subnet UID to disable commit-reveal weights for.

        Raises:
            RuntimeError: If commit-reveal weights remain enabled after the update.
        """
        logger.info("Disabling commit-reveal weights on subnet %d", netuid)
        async with self._turbobt_client() as client:
            result = await client.subtensor.admin_utils.sudo_set_commit_reveal_weights_enabled(
                netuid=netuid,
                enabled=False,
                wallet=SUDO_WALLET,
            )
            await result.wait_for_finalization()
        value = await self.get_storage(ChainStorage.COMMIT_REVEAL_WEIGHTS_ENABLED, netuid)
        if bool(value):
            raise RuntimeError(f"CommitRevealWeightsEnabled is still True for subnet {netuid} after sudo call.")
        logger.info("Commit-reveal weights disabled on subnet %d", netuid)

    async def add_stake(self, wallet: Wallet, netuid: int, hotkey_ss58: str, amount_tao: int) -> None:
        """
        Stake TAO for a hotkey on a subnet.

        Args:
            wallet: Wallet to stake from.
            netuid: Subnet UID to stake on.
            hotkey_ss58: SS58 address of the hotkey to stake for.
            amount_tao: Amount to stake in TAO.
        """
        logger.info("Staking %d TAO for hotkey %s on subnet %d", amount_tao, hotkey_ss58, netuid)
        async with self._turbobt_client() as client:
            result = await client.subtensor.subtensor_module.add_stake(
                hotkey=hotkey_ss58,
                netuid=netuid,
                amount_staked=amount_tao * _RAO_PER_TAO,
                wallet=wallet,
            )
            await result.wait_for_finalization()

    async def remove_stake(self, wallet: Wallet, netuid: int, hotkey_ss58: str, amount_tao: int) -> None:
        """
        Remove staked TAO for a hotkey on a subnet.

        Args:
            wallet: Wallet to unstake from.
            netuid: Subnet UID to unstake on.
            hotkey_ss58: SS58 address of the hotkey to unstake for.
            amount_tao: Amount to unstake in TAO.
        """
        logger.info("Unstaking %d TAO for hotkey %s on subnet %d", amount_tao, hotkey_ss58, netuid)
        async with self._turbobt_client() as client:
            result = await client.subtensor.subtensor_module.remove_stake(
                hotkey=hotkey_ss58,
                netuid=netuid,
                amount_unstaked=amount_tao * _RAO_PER_TAO,
                wallet=wallet,
            )
            await result.wait_for_finalization()

    async def set_commitment(self, wallet: Wallet, netuid: int, data: str) -> None:
        """
        Set a commitment for a hotkey on a subnet.

        Args:
            wallet: Wallet to set the commitment for.
            netuid: Subnet UID.
            data: Commitment data string.
        """
        logger.info("Setting commitment on subnet %d for %s", netuid, wallet.hotkey.ss58_address)
        async with self._turbobt_client() as client:
            await client.subnet(netuid).commitments.set(data.encode(), wallet=wallet)

    async def set_revealed_commitment(self, wallet: Wallet, netuid: int, data: str, blocks_until_reveal: int) -> None:
        """
        Set a revealed commitment for a hotkey on a subnet.

        Args:
            wallet: Wallet to set the commitment for.
            netuid: Subnet UID.
            data: Commitment data string.
            blocks_to_reveal: Number of blocks to reveal the commitment.
        """
        logger.info("Setting revealed commitment on subnet %d for %s", netuid, wallet.hotkey.ss58_address)
        async with self._turbobt_client() as client:
            await client.subnet(netuid).commitments.set_revealed(
                data, blocks_until_reveal=blocks_until_reveal, wallet=wallet
            )

    async def wait_for_commitment_reveal(self, netuid: int, expected_count: int) -> None:
        logger.info("Waiting for commitments to be revealed")
        async with self._turbobt_client() as client:
            async with asyncio.timeout(30):
                while True:
                    revealed_commitments = await client.subnet(netuid).commitments.fetch_revealed()
                    if len(revealed_commitments) == expected_count:
                        break
                    await asyncio.sleep(1)

    # ---- Storage operations (async) ----

    async def get_storage(self, storage: ChainStorage, *params: object) -> object:
        """
        Read a value from chain storage.

        Args:
            storage: The storage key to query.
            *params: Additional parameters for parameterized storage entries (e.g., netuid).

        Returns:
            The storage value.
        """
        logger.info("Getting storage %s", storage.value)
        async with self._turbobt_client() as client:
            return await client.subtensor.state.getStorage(storage.value, *params)

    async def set_weights_rate_limit(self, netuid: int, rate_limit: int) -> None:
        """
        Set the weights rate limit for a subnet via sudo call.

        Args:
            netuid: Subnet UID.
            rate_limit: Rate limit value in blocks.
        """
        logger.info("Setting weights rate limit to %d on subnet %d", rate_limit, netuid)
        async with self._turbobt_client() as client:
            result = await client.subtensor.admin_utils.sudo_set_weights_set_rate_limit(
                netuid=netuid,
                weights_set_rate_limit=rate_limit,
                wallet=SUDO_WALLET,
            )
            await result.wait_for_finalization()

    async def _set_next_unsigned_at(self, block_number: int) -> None:
        """
        Set the block at which the drand offchain worker resumes fetching pulses.
        """
        logger.info("Setting Drand.NextUnsignedAt to %d", block_number)
        await self._set_storage(
            storage=ChainStorage.DRAND_NEXT_UNSIGNED_AT,
            storage_value=f"0x{block_number.to_bytes(4, byteorder='little', signed=False).hex()}",
        )

    async def offset_drand_next_unsigned_at(self):
        """
        Phase 1 of drand workaround — see localchain/README.md#drand-workaround
        """
        current_block = await self.get_current_block_number()
        await self._set_next_unsigned_at(current_block + _DRAND_WORKER_MARGIN)

    async def _reset_drand_stored_round(self, round_number: int) -> None:
        """
        Point the drand offchain worker at ``round_number`` by overwriting
        Drand.LastStoredRound and Drand.OldestStoredRound.
        """
        logger.info("Setting Drand.LastStoredRound to %d", round_number)
        await self._set_storage(
            storage=ChainStorage.DRAND_LAST_STORED_ROUND,
            storage_value=f"0x{round_number.to_bytes(8, byteorder='little', signed=False).hex()}",
        )

        logger.info("Setting Drand.OldestStoredRound to %d", round_number)
        await self._set_storage(
            storage=ChainStorage.DRAND_OLDEST_STORED_ROUND,
            storage_value=f"0x{round_number.to_bytes(8, byteorder='little', signed=False).hex()}",
        )

    async def synchronize_drand_last_stored_round(self) -> None:
        """
        Phase 2 of drand workaround — see localchain/README.md#drand-workaround.

        On the current localnet runtime the worker no longer catches up from a stale snapshot
        round on its own — it stalls after a single batch — and if it wakes on the stale round it
        floods the chain with pulse extrinsics, which can starve the pin writes and deadlock. So
        this first pushes the worker's wake block far out (while it is still idle behind the phase 1
        margin), pins the stored round to the current real drand round, wakes the worker again, and
        only then verifies it is tracking the current round, re-pinning as a safety net.

        Raises:
            RuntimeError: If the worker never starts tracking the current round.
        """
        current_block = await self.get_current_block_number()
        await self._set_next_unsigned_at(current_block + _DRAND_SYNC_HOLD_MARGIN)

        pinned_round = bittensor_drand.get_latest_round() - 1
        await self._reset_drand_stored_round(pinned_round)

        wake_block = (await self.get_current_block_number()) + _DRAND_WAKE_DELAY
        await self._set_next_unsigned_at(wake_block)
        logger.info("Waiting for block to reach Drand.NextUnsignedAt: %d", wake_block)
        for _ in range(_DRAND_SYNC_MAX_ATTEMPTS):
            if (await self.get_current_block_number()) >= wake_block:
                break
            await asyncio.sleep(1)

        for _ in range(_DRAND_SYNC_MAX_ATTEMPTS):
            latest_round = bittensor_drand.get_latest_round()
            stored_round = cast(int, await self.get_storage(ChainStorage.DRAND_LAST_STORED_ROUND))
            gap = latest_round - stored_round
            if gap > _DRAND_MAX_ACCEPTABLE_GAP:
                logger.warning("Drand worker woke on a stale round (%d behind); re-pinning to current", gap)
                pinned_round = latest_round - 1
                await self._reset_drand_stored_round(pinned_round)
            elif stored_round > pinned_round:
                logger.info("Drand worker is tracking the current round (stored %d)", stored_round)
                return
            await asyncio.sleep(1)

        raise RuntimeError("Drand worker did not start tracking the current round in time")

    async def set_tempo(self, netuid: int, tempo: int) -> None:
        """
        Set the tempo (epoch length) for a subnet via sudo call.

        Args:
            netuid: Subnet UID.
            tempo: Tempo value in blocks.
        """
        logger.info("Setting tempo to %d on subnet %d", tempo, netuid)
        async with self._turbobt_client() as client:
            result = await client.subtensor.admin_utils.sudo_set_tempo(
                netuid=netuid,
                tempo=tempo,
                wallet=SUDO_WALLET,
            )
            await result.wait_for_finalization()

    async def set_max_registrations_per_block(self, netuid: int, max_regs: int) -> None:
        """
        Set the maximum number of neuron registrations allowed per block on a subnet.

        Args:
            netuid: Subnet UID.
            max_regs: Maximum registrations per block.

        Raises:
            RuntimeError: If the value is not updated successfully.
        """
        logger.info("Setting max registrations per block to %d on subnet %d", max_regs, netuid)
        await self._set_storage(
            storage=ChainStorage.MAX_REGISTRATIONS_PER_BLOCK,
            storage_value=f"0x{max_regs.to_bytes(2, byteorder='little', signed=False).hex()}",
            params=[netuid],
        )

    async def set_target_registrations_per_interval(self, netuid: int, target: int) -> None:
        """
        Set the target registrations per interval for a subnet.

        Args:
            netuid: Subnet UID.
            target: Target registrations per interval.

        Raises:
            RuntimeError: If the value is not updated successfully.
        """
        logger.info("Setting target registrations per interval to %d on subnet %d", target, netuid)
        await self._set_storage(
            storage=ChainStorage.TARGET_REGISTRATIONS_PER_INTERVAL,
            storage_value=f"0x{target.to_bytes(2, byteorder='little', signed=False).hex()}",
            params=[netuid],
        )

    async def set_tx_rate_limit(self, netuid: int, rate_limit: int) -> None:
        """
        Set the transaction rate limit for a subnet via sudo storage update.

        Args:
            netuid: Subnet UID.
            rate_limit: Transaction rate limit value in blocks.

        Raises:
            RuntimeError: If the rate limit is not updated successfully.
        """
        logger.info("Setting tx rate limit to %d on subnet %d", rate_limit, netuid)
        await self._set_storage(
            storage=ChainStorage.TX_RATE_LIMIT,
            storage_value=f"0x{rate_limit.to_bytes(8, byteorder='little', signed=False).hex()}",
            params=[netuid],
        )

    async def set_max_burn(self, netuid: int, max_burn_rao: int) -> None:
        """
        Cap the maximum registration burn for a subnet via sudo call.

        Each burned registration swaps the burn cost from TAO into the subnet's
        alpha reserve, and the burn ramps up (BurnIncreaseMult) after every
        registration. Left unbounded, bulk registration drains the alpha reserve
        below the swap pallet's MinimumReserve and fails with ReservesTooLow.
        Capping the burn low keeps each swap tiny so the reserve stays healthy.

        Args:
            netuid: Subnet UID.
            max_burn_rao: Maximum burn in RAO. Must exceed the chain's
                MaxBurnLowerBound (0.1 TAO).
        """
        logger.info("Setting max burn to %d on subnet %d", max_burn_rao, netuid)
        async with self._turbobt_client() as client:
            result = await client.subtensor.sudo.sudo(
                "AdminUtils",
                "sudo_set_max_burn",
                {"netuid": netuid, "max_burn": max_burn_rao},
                wallet=SUDO_WALLET,
            )
            await result.wait_for_finalization()

    async def set_serving_rate_limit(self, netuid: int, rate_limit: int) -> None:
        """
        Set the serving rate limit for a subnet via sudo storage update.

        Args:
            netuid: Subnet UID.
            rate_limit: Rate limit value in blocks.

        Raises:
            RuntimeError: If the rate limit is not updated successfully.
        """
        logger.info("Setting serving rate limit to %d on subnet %d", rate_limit, netuid)
        await self._set_storage(
            storage=ChainStorage.SERVING_RATE_LIMIT,
            storage_value=f"0x{rate_limit.to_bytes(8, byteorder='little', signed=False).hex()}",
            params=[netuid],
        )

        value = await self.get_storage(ChainStorage.SERVING_RATE_LIMIT, netuid)
        if value != rate_limit:
            raise RuntimeError(f"ServingRateLimit is {value} for subnet {netuid}, expected {rate_limit}")

    async def serve_axon(self, wallet: Wallet, netuid: int, ip: str, port: int) -> None:
        """
        Publish axon info for a registered neuron.

        Args:
            wallet: Wallet whose hotkey is registered on the subnet.
            netuid: Subnet UID.
            ip: Routable IP address to announce.
            port: Port to announce.
        """
        logger.info("Serving axon %s:%d on subnet %d for %s", ip, port, netuid, wallet.hotkey.ss58_address)
        async with self._turbobt_client() as client:
            await client.subnet(netuid).neurons.serve(ip, port, wallet=wallet)

    async def get_total_networks(self) -> int:
        """
        Return the current number of registered networks.
        """
        total_networks = await self.get_storage(ChainStorage.TOTAL_NETWORKS)
        assert isinstance(total_networks, int)
        return total_networks

    async def get_current_block_number(self) -> int:
        """
        Return the current (head) block number from the chain.

        Raises:
            RuntimeError: If the chain header could not be retrieved.
        """
        async with self._turbobt_client() as client:
            header = await client.subtensor.chain.getHeader()
            if header is None:
                raise RuntimeError("Failed to get chain header")
            return header["number"]

    async def get_extrinsic_decoder(self) -> ExtrinsicDecoder:
        """
        Return a callable that decodes a hex-encoded SCALE extrinsic into a dict.

        Initializes the runtime metadata on the shared turbobt client and captures
        the Extrinsic decoder class together with the chain's metadata, so the
        returned decoder is bound to this chain's runtime.
        """
        async with self._turbobt_client() as client:
            await client.subtensor._init_runtime()
            assert client.subtensor._registry is not None
            assert client.subtensor._metadata is not None
            extrinsic_cls = client.subtensor._registry.get_decoder_class("Extrinsic")
            assert extrinsic_cls is not None
            metadata = client.subtensor._metadata

        def _decode(extrinsic_bytes: str) -> dict[str, Any]:
            return cast(
                dict[str, Any],
                extrinsic_cls(
                    data=scalecodec.ScaleBytes(extrinsic_bytes),
                    metadata=metadata,
                ).decode(),
            )

        return _decode

    async def setup_mechanisms(
        self,
        netuid: int,
    ):
        max_allowed_uids = 64
        mechanism_count = 2
        logger.info("Setting up mechanisms on subnet %d", netuid)
        async with self._turbobt_client() as client:
            extrinsic = await client.subtensor.sudo.sudo(
                "AdminUtils",
                "sudo_set_max_allowed_uids",
                {
                    "netuid": netuid,
                    "max_allowed_uids": max_allowed_uids,
                },
                wallet=SUDO_WALLET,
            )
            await extrinsic.wait_for_finalization()

            extrinsic = await client.subtensor.sudo.sudo(
                "AdminUtils",
                "sudo_set_mechanism_count",
                {
                    "netuid": netuid,
                    "mechanism_count": mechanism_count,
                },
                wallet=SUDO_WALLET,
            )
            await extrinsic.wait_for_finalization()

            value = await self.get_storage(ChainStorage.MECHANISM_COUNT_CURRENT, netuid)
            if value != mechanism_count:
                raise RuntimeError(f"MechanismCountCurrent is {value} after sudo call, expected {mechanism_count}")

        logger.info("Mechanisms set up successfully")

    async def get_subnet_hyperparameters(self, netuid: int):
        async with self._turbobt_client() as client:
            return await client.subnet(netuid).get_hyperparameters()

    # ---- Bulk operations (async) ----

    async def batch_transfer(
        self,
        wallet: Wallet,
        destinations: list[tuple[str, int]],
        batch_size: int = 50,
    ) -> None:
        """
        Transfer TAO to multiple destinations using batched extrinsics.

        Groups transfers into sub-batches to stay within block weight limits.
        Each sub-batch is submitted as a single ``Utility.batch_all`` extrinsic.

        Args:
            wallet: Source wallet for all transfers.
            destinations: List of (ss58_address, amount_tao) pairs.
            batch_size: Maximum transfers per batch extrinsic.
        """
        for batch_index, chunk in enumerate(itertools.batched(destinations, batch_size, strict=False)):
            start = batch_index * batch_size + 1
            logger.info("Batch transfer %d-%d of %d", start, start + len(chunk) - 1, len(destinations))
            # Separate client because turbobt Transaction requires client.wallet to be set,
            # and the shared client (_turbobt_client) has wallet=None.
            async with Bittensor(wallet=wallet, uri=self.ws_url) as client:
                async with Transaction(client):
                    for dest_ss58, amount_tao in chunk:
                        result = await client.subtensor.author.submitAndWatchExtrinsic(
                            "Balances",
                            "transfer_keep_alive",
                            {"dest": dest_ss58, "value": amount_tao * _RAO_PER_TAO},
                            key=wallet.coldkey,
                        )
                        await result.wait_for_finalization()

    async def register_neurons_concurrent(
        self,
        wallets: list[Wallet],
        netuid: int,
        batch_size: int = 16,
    ) -> None:
        """
        Register multiple neurons concurrently in batches.

        Each wallet registers independently (different nonces), so
        ``asyncio.gather`` is safe. Registrations are split into
        batches to avoid overwhelming the local chain node.

        Uses immortal era (``era=None``) to prevent "ancient birth block"
        errors when multiple transactions compete for block space.

        Args:
            wallets: Wallets to register as neurons.
            netuid: Subnet UID to register on.
            batch_size: Maximum concurrent registrations per batch.
        """
        for batch_index, batch in enumerate(itertools.batched(wallets, batch_size, strict=False)):
            start = batch_index * batch_size + 1
            logger.info(
                "Registering neurons %d-%d of %d on subnet %d",
                start,
                start + len(batch) - 1,
                len(wallets),
                netuid,
            )
            await asyncio.gather(*(self._register_neuron_immortal(wallet=w, netuid=netuid) for w in batch))

    async def _register_neuron_immortal(self, wallet: Wallet, netuid: int) -> None:
        """Register a neuron using an immortal era to avoid expiration during concurrent registration."""
        async with self._turbobt_client() as client:
            try:
                extrinsic = await asyncio.shield(
                    client.subtensor.subtensor_module.burned_register(
                        netuid=netuid,
                        hotkey=wallet.hotkey.ss58_address,
                        wallet=wallet,
                        era=None,
                    )
                )
                await asyncio.shield(extrinsic.wait_for_finalization())
            except HotKeyAlreadyRegisteredInSubNet:
                logger.info("Hotkey %s already registered on subnet %d, skipping", wallet.hotkey.ss58_address, netuid)

    async def associate_evm_key(self, wallet: Wallet, netuid: int, evm_wallet: LocalAccount) -> None:
        """
        Associate an EVM key with a hotkey on a subnet.

        Args:
            wallet: Wallet (hotkey) to associate the EVM key with.
            netuid: Subnet UID.
            evm_wallet: EVM wallet to associate.
        """
        logger.info(
            "Associating EVM key %s with hotkey %s on subnet %d",
            evm_wallet.address,
            wallet.hotkey.ss58_address,
            netuid,
        )

        hotkey_bytes = bytes.fromhex(ss58_decode(wallet.hotkey.ss58_address))

        block_number = await self.get_current_block_number()
        encoded_block_number = block_number.to_bytes(8, byteorder="little", signed=False)
        block_hash = keccak(encoded_block_number)

        message = hotkey_bytes + block_hash

        signable_message = encode_defunct(primitive=message)
        signed_message = evm_wallet.sign_message(signable_message)
        signature = signed_message.signature.hex()

        async with self._turbobt_client() as client:
            result = await client.subtensor.author.submitAndWatchExtrinsic(
                "SubtensorModule",
                "associate_evm_key",
                {
                    "netuid": netuid,
                    "evm_key": evm_wallet.address,
                    "block_number": block_number,
                    "signature": f"0x{signature}",
                },
                key=wallet.hotkey,
            )
            await result.wait_for_finalization()

    @asynccontextmanager
    async def _turbobt_client(self) -> AsyncIterator[Bittensor]:
        """
        Return the shared turbobt Bittensor client, opening it on first use.

        Yields:
            A connected Bittensor client instance.
        """
        if self._bt_client is None:
            self._bt_client = Bittensor(wallet=None, uri=self.ws_url)
            await self._bt_client.__aenter__()
        yield self._bt_client

    async def _set_storage(
        self,
        storage: ChainStorage,
        storage_value: str,
        params: list[object] | None = None,
    ) -> None:
        pallet_name, storage_name = storage.split(".")
        async with self._turbobt_client() as client:
            await client.subtensor._init_runtime()
            assert client.subtensor._metadata is not None
            pallet = client.subtensor._metadata.get_metadata_pallet(pallet_name)
            storage_function = pallet.get_storage_function(storage_name)
            storage_key = client.subtensor.state._storage_key(pallet, storage_function, params or [])
            result = await client.subtensor.sudo.sudo(
                "System",
                "set_storage",
                {"items": [[storage_key, storage_value]]},
                wallet=SUDO_WALLET,
            )
            await result.wait_for_finalization()

    @staticmethod
    def _create_docker_client(endpoint: DockerContextEndpoint) -> docker.DockerClient:
        kwargs: dict[str, object] = {"base_url": endpoint.raw_host}
        if endpoint.scheme == "ssh":
            kwargs["use_ssh_client"] = True
        return docker.DockerClient(version="auto", **kwargs)

    @staticmethod
    def _resolve_rpc_host(endpoint: DockerContextEndpoint) -> str:
        if endpoint.scheme in {"ssh", "unix", "npipe"}:
            return _HOST
        if endpoint.hostname is None:
            raise RuntimeError(f"Docker context host {endpoint.raw_host!r} does not expose a hostname")
        return endpoint.hostname

    @staticmethod
    def _load_active_docker_context() -> DockerContextEndpoint:
        context_name_process = subprocess.run(
            ["docker", "context", "show"],
            check=True,
            capture_output=True,
            text=True,
        )
        context_name = context_name_process.stdout.strip()
        if not context_name:
            raise RuntimeError("docker context show returned an empty context name")

        inspect_process = subprocess.run(
            ["docker", "context", "inspect", context_name],
            check=True,
            capture_output=True,
            text=True,
        )
        contexts = json.loads(inspect_process.stdout)
        if len(contexts) != 1:
            raise RuntimeError(f"Expected one docker context from inspect, got {len(contexts)}")

        raw_host = contexts[0].get("Endpoints", {}).get("docker", {}).get("Host")
        if not raw_host:
            raise RuntimeError(f"Docker context {context_name!r} has no docker endpoint host")

        parsed = urlparse(raw_host)
        if not parsed.scheme:
            raise RuntimeError(f"Docker context endpoint {raw_host!r} is missing a scheme")

        return DockerContextEndpoint(
            scheme=parsed.scheme,
            raw_host=raw_host,
            hostname=parsed.hostname,
            username=parsed.username,
            port=parsed.port,
        )
