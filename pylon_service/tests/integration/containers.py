from __future__ import annotations

import enum
import json
import logging
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from testcontainers.core.container import DockerContainer
from testcontainers.core.image import DockerImage
from testcontainers.core.wait_strategies import HttpWaitStrategy

from tests.helpers import find_free_port

logger = logging.getLogger(__name__)

_CHAIN_RPC_PORT = 9944
_PYLON_SERVICE_PORT = 8000
_REPO_ROOT = Path(__file__).resolve().parents[3]
_TEST_ENV_PATH = Path(__file__).resolve().parents[1] / ".test-env"


class LocalChainImage(enum.StrEnum):
    """Docker images available for the local subtensor chain."""

    DEFAULT = "ghcr.io/opentensor/subtensor-localnet:main"
    PREPARED = "prepared-localnet:latest"


class LocalChainContainer(DockerContainer):
    """
    Subtensor localnet container with JSON-RPC health check.

    Starts the local Bittensor chain from a Docker image and waits
    until the RPC endpoint is responsive before reporting readiness.
    """

    def __init__(
        self,
        image: LocalChainImage = LocalChainImage.PREPARED,
        startup_timeout: int = 30,
        *,
        host_rpc_port: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(image.value, **kwargs)
        self._host_rpc_port = host_rpc_port if host_rpc_port is not None else find_free_port()
        self.with_bind_ports(_CHAIN_RPC_PORT, self._host_rpc_port)
        self.waiting_for(
            HttpWaitStrategy(_CHAIN_RPC_PORT, "/")
            .with_method("POST")
            .with_body(json.dumps({"id": 1, "jsonrpc": "2.0", "method": "system_health", "params": []}))
            .with_header("Content-Type", "application/json")
            .with_startup_timeout(startup_timeout)
            .with_poll_interval(0.5)
        )

    def _prepared_image_exists(self) -> bool:
        docker_client = self.get_docker_client()
        images = docker_client.client.images.list(name=LocalChainImage.PREPARED)
        return len(images) > 0

    async def ensure_prepared_image(self) -> None:
        """
        Ensure the prepared localchain Docker image exists, building it if necessary.

        If the image is not found locally, runs the prepare_chain script
        to create it from a fresh chain.
        """
        if self._prepared_image_exists():
            return
        logger.warning(
            "Docker image '%s' not found locally — building it now.",
            LocalChainImage.PREPARED,
        )
        from tests.integration.localchain import prepare_chain

        await prepare_chain.main()
        logger.info("Docker image '%s' built successfully", LocalChainImage.PREPARED)

    @property
    def rpc_port(self) -> int:
        return self._host_rpc_port

    @property
    def rpc_host(self) -> str:
        return self.get_container_host_ip()

    @property
    def ws_url(self) -> str:
        return f"ws://{self.rpc_host}:{self.rpc_port}"

    @property
    def http_url(self) -> str:
        return f"http://{self.rpc_host}:{self.rpc_port}"


class PylonServiceContainer(DockerContainer):
    """
    Pylon service container built from Dockerfile.

    Builds the service image from the repository Dockerfile, configures
    it with the required environment variables, and waits for the
    OpenAPI schema endpoint to respond before reporting readiness.
    """

    def __init__(
        self,
        image: str,
        chain_url: str,
        wallets_path: str | Path,
        startup_timeout: int = 30,
        *,
        host_api_port: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(image, **kwargs)
        self._host_api_port = host_api_port if host_api_port is not None else find_free_port()
        self.with_bind_ports(_PYLON_SERVICE_PORT, self._host_api_port)
        self.waiting_for(
            HttpWaitStrategy(_PYLON_SERVICE_PORT, "/schema/openapi.json")
            .with_startup_timeout(startup_timeout)
            .with_poll_interval(0.5)
        )

        self.with_volume_mapping(str(wallets_path), "/app/wallets", "ro")

        envs = {k: v for k, v in dotenv_values(_TEST_ENV_PATH).items() if v is not None}
        envs.update(
            PYLON_BITTENSOR_NETWORK=chain_url,
            PYLON_BITTENSOR_ARCHIVE_NETWORK=chain_url,
            PYLON_BITTENSOR_WALLET_PATH="/app/wallets",
            PYLON_BLOCK_DURATION_SECONDS="0.25",
            PYLON_RECENT_OBJECTS_SOFT_LIMIT_BLOCKS="480",
            PYLON_RECENT_OBJECTS_HARD_LIMIT_BLOCKS="960",
        )
        self.with_envs(**envs)

    @property
    def api_port(self) -> int:
        return self._host_api_port

    @property
    def api_host(self) -> str:
        return self.get_container_host_ip()

    @property
    def api_url(self) -> str:
        return f"http://{self.api_host}:{self.api_port}"

    @staticmethod
    def build_image() -> DockerImage:
        """
        Build the Pylon service Docker image from the repository Dockerfile.

        Returns:
            A DockerImage that can be used as `str(image)` for the container constructor.
        """
        logger.info("Building Pylon service Docker image from %s", _REPO_ROOT)
        image = DockerImage(
            path=str(_REPO_ROOT),
            dockerfile_path="pylon_service/Dockerfile",
            tag="pylon-service-test:latest",
            clean_up=False,
        )
        image.build()
        logger.info("Pylon service image built: %s", image.tag)
        return image
