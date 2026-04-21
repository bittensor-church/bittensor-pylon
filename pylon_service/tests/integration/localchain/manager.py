from __future__ import annotations

import enum
import json
import logging
import subprocess
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from types import TracebackType
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import docker
from bittensor_wallet import Wallet
from turbobt.client import Bittensor
from turbobt.subtensor.exceptions import HotKeyAlreadyRegisteredInSubNet

from tests.integration.containers import LocalChainContainer, LocalChainImage

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from docker.models.containers import Container

_HOST = "localhost"
_CONTACT_TEST_AXON_IP = "1.1.1.1"
_CONTACT_TEST_AXON_PORT = 12345

_RAO_PER_TAO = 1_000_000_000


class ChainStorage(enum.StrEnum):
    ADMIN_FREEZE_WINDOW = "SubtensorModule.AdminFreezeWindow"
    COMMIT_REVEAL_WEIGHTS_ENABLED = "SubtensorModule.CommitRevealWeightsEnabled"
    DRAND_LAST_STORED_ROUND = "Drand.LastStoredRound"
    DRAND_NEXT_UNSIGNED_AT = "Drand.NextUnsignedAt"
    DRAND_OLDEST_STORED_ROUND = "Drand.OldestStoredRound"
    SERVING_RATE_LIMIT = "SubtensorModule.ServingRateLimit"
    SUBTOKEN_ENABLED = "SubtensorModule.SubtokenEnabled"
    TOTAL_NETWORKS = "SubtensorModule.TotalNetworks"
    WEIGHTS_SET_RATE_LIMIT = "SubtensorModule.WeightsSetRateLimit"


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

    async def disable_admin_freeze_window(self, sudo_wallet: Wallet) -> None:
        """
        Set AdminFreezeWindow to 0 via sudo set_storage call.

        On a fresh localnet the default AdminFreezeWindow is 10 blocks,
        which can cause sudo calls to silently fail. Setting it to 0
        eliminates this problem for all subsequent sudo operations.

        Args:
            sudo_wallet: Wallet with sudo privileges (typically alice on localnet).

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
                wallet=sudo_wallet,
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

    async def enable_subtokens(self, sudo_wallet: Wallet, netuid: int) -> None:
        """
        Enable subtokens on a subnet via sudo call.

        The localnet image has SubtokenEnabled=False by default, which
        blocks staking. Requires AdminFreezeWindow=0 to avoid silent failures.

        Args:
            sudo_wallet: Wallet with sudo privileges.
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
                wallet=sudo_wallet,
            )
            await result.wait_for_finalization()

            value = await client.subtensor.state.getStorage(ChainStorage.SUBTOKEN_ENABLED, netuid)
            if not bool(value):
                raise RuntimeError(
                    f"SubtokenEnabled is still False for subnet {netuid} after sudo call. "
                    "The inner sudo call likely failed silently."
                )
        logger.info("Subtokens enabled on subnet %d", netuid)

    async def enable_commit_reveal_weights(self, sudo_wallet: Wallet, netuid: int) -> None:
        """
        Enable commit-reveal weights on a subnet via the admin hyperparameter extrinsic.

        Args:
            sudo_wallet: Wallet with sudo privileges.
            netuid: Subnet UID to enable commit-reveal weights for.

        Raises:
            RuntimeError: If commit-reveal weights are still disabled after the update.
        """
        logger.info("Enabling commit-reveal weights on subnet %d", netuid)
        async with self._turbobt_client() as client:
            result = await client.subtensor.admin_utils.sudo_set_commit_reveal_weights_enabled(
                netuid=netuid,
                enabled=True,
                wallet=sudo_wallet,
            )
            await result.wait_for_finalization()
        value = await self.get_storage(ChainStorage.COMMIT_REVEAL_WEIGHTS_ENABLED, netuid)
        if not bool(value):
            raise RuntimeError(f"CommitRevealWeightsEnabled is still False for subnet {netuid} after sudo call.")
        logger.info("Commit-reveal weights enabled on subnet %d", netuid)

    async def disable_commit_reveal_weights(self, sudo_wallet: Wallet, netuid: int) -> None:
        """
        Disable commit-reveal weights on a subnet via the admin hyperparameter extrinsic.

        Args:
            sudo_wallet: Wallet with sudo privileges.
            netuid: Subnet UID to disable commit-reveal weights for.

        Raises:
            RuntimeError: If commit-reveal weights remain enabled after the update.
        """
        logger.info("Disabling commit-reveal weights on subnet %d", netuid)
        async with self._turbobt_client() as client:
            result = await client.subtensor.admin_utils.sudo_set_commit_reveal_weights_enabled(
                netuid=netuid,
                enabled=False,
                wallet=sudo_wallet,
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
            result = await client.subnet(netuid).commitments.set(data.encode(), wallet=wallet)
            await result.wait_for_finalization()

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

    async def set_weights_rate_limit(self, sudo_wallet: Wallet, netuid: int, rate_limit: int) -> None:
        """
        Set the weights rate limit for a subnet via sudo call.

        Args:
            sudo_wallet: Wallet with sudo privileges.
            netuid: Subnet UID.
            rate_limit: Rate limit value in blocks.
        """
        logger.info("Setting weights rate limit to %d on subnet %d", rate_limit, netuid)
        async with self._turbobt_client() as client:
            result = await client.subtensor.admin_utils.sudo_set_weights_set_rate_limit(
                netuid=netuid,
                weights_set_rate_limit=rate_limit,
                wallet=sudo_wallet,
            )
            await result.wait_for_finalization()

    async def set_drand_last_stored_round(self, sudo_wallet: Wallet, round_number: int) -> None:
        """
        Set the latest Drand round known to the local chain via sudo storage update.

        Args:
            sudo_wallet: Wallet with sudo privileges.
            round_number: Drand round number to store.
        """
        logger.info("Setting Drand.LastStoredRound to %d", round_number)
        await self._set_storage(
            sudo_wallet=sudo_wallet,
            pallet_name="Drand",
            storage_name="LastStoredRound",
            storage_value=f"0x{round_number.to_bytes(8, byteorder='little', signed=False).hex()}",
        )

    async def set_drand_oldest_stored_round(self, sudo_wallet: Wallet, round_number: int) -> None:
        """
        Set the oldest Drand round known to the local chain via sudo storage update.

        Args:
            sudo_wallet: Wallet with sudo privileges.
            round_number: Drand round number to store.
        """
        logger.info("Setting Drand.OldestStoredRound to %d", round_number)
        await self._set_storage(
            sudo_wallet=sudo_wallet,
            pallet_name="Drand",
            storage_name="OldestStoredRound",
            storage_value=f"0x{round_number.to_bytes(8, byteorder='little', signed=False).hex()}",
        )

    async def set_drand_next_unsigned_at(self, sudo_wallet: Wallet, block_number: int) -> None:
        """
        Set the next block at which an unsigned Drand extrinsic should be submitted.

        Args:
            sudo_wallet: Wallet with sudo privileges.
            block_number: Target block number.

        Raises:
            RuntimeError: If the stored value does not match the expected value after write.
        """
        logger.info("Setting Drand.NextUnsignedAt to %d", block_number)
        await self._set_storage(
            sudo_wallet=sudo_wallet,
            pallet_name="Drand",
            storage_name="NextUnsignedAt",
            storage_value=f"0x{block_number.to_bytes(4, byteorder='little', signed=False).hex()}",
        )

    async def set_tempo(self, sudo_wallet: Wallet, netuid: int, tempo: int) -> None:
        """
        Set the tempo (epoch length) for a subnet via sudo call.

        Args:
            sudo_wallet: Wallet with sudo privileges.
            netuid: Subnet UID.
            tempo: Tempo value in blocks.
        """
        logger.info("Setting tempo to %d on subnet %d", tempo, netuid)
        async with self._turbobt_client() as client:
            result = await client.subtensor.admin_utils.sudo_set_tempo(
                netuid=netuid,
                tempo=tempo,
                wallet=sudo_wallet,
            )
            await result.wait_for_finalization()

    async def set_serving_rate_limit(self, sudo_wallet: Wallet, netuid: int, rate_limit: int) -> None:
        """
        Set the serving rate limit for a subnet via sudo storage update.

        Args:
            sudo_wallet: Wallet with sudo privileges.
            netuid: Subnet UID.
            rate_limit: Rate limit value in blocks.

        Raises:
            RuntimeError: If the rate limit is not updated successfully.
        """
        logger.info("Setting serving rate limit to %d on subnet %d", rate_limit, netuid)
        await self._set_storage(
            sudo_wallet=sudo_wallet,
            storage_name="ServingRateLimit",
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

    async def prepare_contact_write_subnets(
        self,
        sudo_wallet: Wallet,
        participant_wallets: list[Wallet],
        transfer_amount_tao: int = 100_000,
        stake_amount_tao: int = 10_000,
    ) -> tuple[int, int]:
        """
        Prepare one direct-weights subnet and one commit-reveal subnet for contact integration tests.

        Args:
            sudo_wallet: The sudo wallet and subnet owner.
            participant_wallets: Wallets that should be funded and registered on both subnets.
            transfer_amount_tao: TAO amount to transfer to non-owner participants for registration costs.
            stake_amount_tao: TAO amount to stake for the owner on each subnet.

        Returns:
            A pair of netuids `(direct_netuid, commit_netuid)`.
        """
        await self.disable_admin_freeze_window(sudo_wallet=sudo_wallet)

        for wallet in participant_wallets:
            if wallet.coldkeypub.ss58_address == sudo_wallet.coldkeypub.ss58_address:
                continue
            await self.transfer(
                wallet=sudo_wallet,
                destination_ss58=wallet.coldkeypub.ss58_address,
                amount_tao=transfer_amount_tao,
            )

        direct_netuid = await self.get_total_networks()
        await self.register_subnet(wallet=sudo_wallet)
        commit_netuid = await self.get_total_networks()
        await self.register_subnet(wallet=sudo_wallet)

        for netuid in (direct_netuid, commit_netuid):
            for wallet in participant_wallets:
                await self.register_neuron(wallet=wallet, netuid=netuid)
            await self.enable_subtokens(sudo_wallet=sudo_wallet, netuid=netuid)

        await self.add_stake(
            wallet=sudo_wallet,
            netuid=direct_netuid,
            hotkey_ss58=sudo_wallet.hotkey.ss58_address,
            amount_tao=stake_amount_tao,
        )
        await self.add_stake(
            wallet=sudo_wallet,
            netuid=commit_netuid,
            hotkey_ss58=sudo_wallet.hotkey.ss58_address,
            amount_tao=stake_amount_tao,
        )
        await self.disable_commit_reveal_weights(sudo_wallet=sudo_wallet, netuid=direct_netuid)
        await self.enable_commit_reveal_weights(sudo_wallet=sudo_wallet, netuid=commit_netuid)
        await self.set_serving_rate_limit(sudo_wallet=sudo_wallet, netuid=direct_netuid, rate_limit=0)
        await self.serve_axon(
            wallet=sudo_wallet,
            netuid=direct_netuid,
            ip=_CONTACT_TEST_AXON_IP,
            port=_CONTACT_TEST_AXON_PORT,
        )

        return direct_netuid, commit_netuid

    # ---- Private helpers ----

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
        sudo_wallet: Wallet,
        storage_name: str,
        storage_value: str,
        pallet_name: str = "SubtensorModule",
        params: list[object] | None = None,
    ) -> None:
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
                wallet=sudo_wallet,
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
