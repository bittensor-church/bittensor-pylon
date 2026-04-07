from __future__ import annotations

import enum
import json
import logging
import subprocess
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from types import TracebackType
from urllib.parse import urlparse

import docker
import docker.errors
import httpx
from bittensor_wallet import Wallet
from turbobt.client import Bittensor
from turbobt.subtensor.exceptions import HotKeyAlreadyRegisteredInSubNet

from tests.helpers import find_free_port

logger = logging.getLogger(__name__)

_HOST = "localhost"
_CHAIN_RPC_PORT = 9944
_CONTACT_TEST_AXON_IP = "1.1.1.1"
_CONTACT_TEST_AXON_PORT = 12345

_RAO_PER_TAO = 1_000_000_000


class ChainStorage(enum.StrEnum):
    ADMIN_FREEZE_WINDOW = "SubtensorModule.AdminFreezeWindow"
    COMMIT_REVEAL_WEIGHTS_ENABLED = "SubtensorModule.CommitRevealWeightsEnabled"
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
    Manages a local subtensor Docker container for integration tests.

    Provides Docker lifecycle management (start, stop, snapshot) and
    chain operation methods for building custom chain states. Docker
    operations are synchronous; chain operations are async and use
    the turbobt library.
    """

    IMAGE = "ghcr.io/opentensor/subtensor-localnet:main"
    _CONTAINER_NAME_PREFIX = "pylon-integration-test"

    def __init__(
        self,
        port: int | None = None,
        image: str = IMAGE,
        startup_timeout: float = 60.0,
    ) -> None:
        self.port = port if port is not None else find_free_port()
        self._image = image
        self._startup_timeout = startup_timeout
        self._container_name = f"{self._CONTAINER_NAME_PREFIX}-{self.port}"
        self._context_endpoint = self._load_active_docker_context()
        self._docker = self._create_docker_client(self._context_endpoint)
        self._rpc_host = self._resolve_rpc_host(self._context_endpoint)
        self._ssh_tunnel: subprocess.Popen[str] | None = None

    def __enter__(self) -> LocalChainManager:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.stop()

    @property
    def ws_url(self) -> str:
        return f"ws://{self._rpc_host}:{self.port}"

    @property
    def http_url(self) -> str:
        return f"http://{self._rpc_host}:{self.port}"

    # ---- Docker lifecycle (sync) ----

    def start(self) -> None:
        """
        Start the local subtensor Docker container and wait until it's ready.

        Uses the image and startup_timeout configured in __init__.

        Raises:
            RuntimeError: If the chain doesn't become ready within the timeout.
        """
        logger.info("Starting container from image %s on port %d", self._image, self.port)
        run_kwargs = {
            "command": ["True", "--no-purge"],
            "name": self._container_name,
            "detach": True,
        }
        if self._context_endpoint.scheme != "ssh":
            run_kwargs["ports"] = {f"{_CHAIN_RPC_PORT}/tcp": self.port}

        container = self._docker.containers.run(self._image, **run_kwargs)

        if self._context_endpoint.scheme == "ssh":
            self._start_ssh_tunnel(container)

        deadline = time.monotonic() + self._startup_timeout
        while time.monotonic() < deadline:
            with suppress(httpx.RequestError):
                response = httpx.post(
                    self.http_url,
                    json={"id": 1, "jsonrpc": "2.0", "method": "system_health", "params": []},
                    timeout=2.0,
                )
                if response.status_code == 200:
                    logger.info("Container ready on port %d", self.port)
                    return
            time.sleep(0.5)

        self.stop()
        raise RuntimeError(f"Local chain did not start within {self._startup_timeout}s on port {self.port}")

    def stop(self) -> None:
        """
        Stop and remove the Docker container.
        """
        self._stop_ssh_tunnel()
        try:
            container = self._docker.containers.get(self._container_name)
            logger.info("Removing container %s", self._container_name)
            container.remove(force=True)
        except docker.errors.NotFound:
            pass

    def make_snapshot(self, image_name: str) -> None:
        """
        Stop the container and commit it as a Docker image.

        The resulting image can be started with 'True --no-purge' arguments
        to preserve chain state.

        Args:
            image_name: Name (and optional tag) for the snapshot image.

        Raises:
            docker.errors.APIError: If any Docker operation fails.
            docker.errors.NotFound: If the container does not exist.
        """
        logger.info("Creating snapshot image %s", image_name)
        container = self._docker.containers.get(self._container_name)
        repository, _, tag = image_name.partition(":")
        container.commit(repository=repository, tag=tag or None)
        container.remove(force=True)
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
        async with self._turbobt_client(wallet=sudo_wallet) as client:
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
        async with self._turbobt_client(wallet=wallet) as client:
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
        async with self._turbobt_client(wallet=wallet) as client:
            await client.subnets.register(wallet=wallet)

    async def register_neuron(self, wallet: Wallet, netuid: int) -> None:
        """
        Register a neuron on a subnet via burned registration.

        Args:
            wallet: Wallet for the neuron to register.
            netuid: Subnet UID to register on.
        """
        logger.info("Registering neuron %s on subnet %d", wallet.hotkey.ss58_address, netuid)
        async with self._turbobt_client(wallet=wallet) as client:
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
        async with self._turbobt_client(wallet=sudo_wallet) as client:
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
        Enable commit-reveal weights on a subnet via sudo storage update.

        Args:
            sudo_wallet: Wallet with sudo privileges.
            netuid: Subnet UID to enable commit-reveal weights for.

        Raises:
            RuntimeError: If commit-reveal weights are still disabled after the update.
        """
        logger.info("Enabling commit-reveal weights on subnet %d", netuid)
        await self._set_storage(
            sudo_wallet=sudo_wallet,
            storage_name="CommitRevealWeightsEnabled",
            storage_value="0x01",
            params=[netuid],
        )
        value = await self.get_storage(ChainStorage.COMMIT_REVEAL_WEIGHTS_ENABLED, netuid)
        if not bool(value):
            raise RuntimeError(f"CommitRevealWeightsEnabled is still False for subnet {netuid} after sudo call.")
        logger.info("Commit-reveal weights enabled on subnet %d", netuid)

    async def disable_commit_reveal_weights(self, sudo_wallet: Wallet, netuid: int) -> None:
        """
        Disable commit-reveal weights on a subnet via sudo storage update.

        Args:
            sudo_wallet: Wallet with sudo privileges.
            netuid: Subnet UID to disable commit-reveal weights for.

        Raises:
            RuntimeError: If commit-reveal weights remain enabled after the update.
        """
        logger.info("Disabling commit-reveal weights on subnet %d", netuid)
        await self._set_storage(
            sudo_wallet=sudo_wallet,
            storage_name="CommitRevealWeightsEnabled",
            storage_value="0x00",
            params=[netuid],
        )
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
        async with self._turbobt_client(wallet=wallet) as client:
            result = await client.subtensor.subtensor_module.add_stake(
                hotkey=hotkey_ss58,
                netuid=netuid,
                amount_staked=amount_tao * _RAO_PER_TAO,
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
        async with self._turbobt_client(wallet=wallet) as client:
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
        async with self._turbobt_client(wallet=sudo_wallet) as client:
            result = await client.subtensor.admin_utils.sudo_set_weights_set_rate_limit(
                netuid=netuid,
                weights_set_rate_limit=rate_limit,
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
        async with self._turbobt_client(wallet=wallet) as client:
            await client.subnet(netuid).neurons.serve(ip, port, wallet=wallet)

    async def get_total_networks(self) -> int:
        """
        Return the current number of registered networks.
        """
        total_networks = await self.get_storage(ChainStorage.TOTAL_NETWORKS)
        assert isinstance(total_networks, int)
        return total_networks

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
    async def _turbobt_client(self, wallet: Wallet | None = None) -> AsyncIterator[Bittensor]:
        """
        Create a turbobt Bittensor client connected to the local chain.

        Args:
            wallet: Optional wallet for signed operations.

        Yields:
            A connected Bittensor client instance.
        """
        async with Bittensor(wallet=wallet, uri=self.ws_url) as client:
            yield client

    async def _set_storage(
        self,
        sudo_wallet: Wallet,
        storage_name: str,
        storage_value: str,
        params: list[object] | None = None,
    ) -> None:
        async with self._turbobt_client(wallet=sudo_wallet) as client:
            await client.subtensor._init_runtime()
            assert client.subtensor._metadata is not None
            pallet = client.subtensor._metadata.get_metadata_pallet("SubtensorModule")
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

    def _start_ssh_tunnel(self, container: docker.models.containers.Container) -> None:
        if self._context_endpoint.scheme != "ssh":
            return
        container_ip = self._get_container_ip(container)
        remote = self._ssh_remote()
        command = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ExitOnForwardFailure=yes",
            "-N",
            "-L",
            f"{self.port}:{container_ip}:{_CHAIN_RPC_PORT}",
        ]
        if self._context_endpoint.port is not None:
            command.extend(["-p", str(self._context_endpoint.port)])
        command.append(remote)
        logger.info("Starting SSH tunnel for chain RPC via %s", remote)
        self._ssh_tunnel = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )

    def _stop_ssh_tunnel(self) -> None:
        if self._ssh_tunnel is None:
            return
        if self._ssh_tunnel.poll() is None:
            self._ssh_tunnel.terminate()
            try:
                self._ssh_tunnel.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._ssh_tunnel.kill()
                self._ssh_tunnel.wait(timeout=5)
        self._ssh_tunnel = None

    def _get_container_ip(self, container: docker.models.containers.Container) -> str:
        container.reload()
        network_settings = container.attrs.get("NetworkSettings", {})
        if ip_address := network_settings.get("IPAddress"):
            return ip_address

        networks = network_settings.get("Networks", {})
        for network in networks.values():
            if ip_address := network.get("IPAddress"):
                return ip_address
        raise RuntimeError(f"Could not determine IP address for container {self._container_name}")

    def _ssh_remote(self) -> str:
        if self._context_endpoint.hostname is None:
            raise RuntimeError(f"SSH docker context {self._context_endpoint.raw_host!r} is missing a host")
        if self._context_endpoint.username:
            return f"{self._context_endpoint.username}@{self._context_endpoint.hostname}"
        return self._context_endpoint.hostname
