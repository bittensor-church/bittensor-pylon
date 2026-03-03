from __future__ import annotations

import enum
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from types import TracebackType

import docker
import docker.errors
import httpx
from bittensor_wallet import Wallet
from turbobt.client import Bittensor
from turbobt.subtensor.exceptions import HotKeyAlreadyRegisteredInSubNet

from tests.helpers import find_free_port

logger = logging.getLogger(__name__)

_HOST = "localhost"

_RAO_PER_TAO = 1_000_000_000


class ChainStorage(enum.StrEnum):
    ADMIN_FREEZE_WINDOW = "SubtensorModule.AdminFreezeWindow"
    SUBTOKEN_ENABLED = "SubtensorModule.SubtokenEnabled"
    WEIGHTS_SET_RATE_LIMIT = "SubtensorModule.WeightsSetRateLimit"


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
        self._docker = docker.from_env()

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
        return f"ws://{_HOST}:{self.port}"

    @property
    def http_url(self) -> str:
        return f"http://{_HOST}:{self.port}"

    # ---- Docker lifecycle (sync) ----

    def start(self) -> None:
        """
        Start the local subtensor Docker container and wait until it's ready.

        Uses the image and startup_timeout configured in __init__.

        Raises:
            RuntimeError: If the chain doesn't become ready within the timeout.
        """
        logger.info("Starting container from image %s on port %d", self._image, self.port)
        self._docker.containers.run(
            self._image,
            command=["True", "--no-purge"],
            name=self._container_name,
            ports={"9944/tcp": self.port},
            detach=True,
        )

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
        try:
            container = self._docker.containers.get(self._container_name)
            logger.info("Stopping container %s", self._container_name)
            container.stop()
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
        container.stop()
        repository, _, tag = image_name.partition(":")
        container.commit(repository=repository, tag=tag or None)
        container.remove()
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
