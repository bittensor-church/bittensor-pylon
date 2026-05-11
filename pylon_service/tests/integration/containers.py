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
_MITMPROXY_LISTEN_PORT = 9944
_MITMPROXY_RECORDER_PORT = 8474
_REPO_ROOT = Path(__file__).resolve().parents[3]
_TEST_ENV_PATH = Path(__file__).resolve().parents[1] / ".test-env"
_MITMPROXY_ADDON_PATH = Path(__file__).resolve().parent / "mitmproxy" / "addon" / "ws_recorder.py"
_MITMPROXY_IMAGE = "mitmproxy/mitmproxy:11.1.3"


class BaseDockerContainer(DockerContainer):
    """
    Common base for our project's Docker containers.

    Provides shared helpers on top of `testcontainers.DockerContainer`,
    e.g. typed access to the network alias attached via `with_network_aliases`.
    """

    @property
    def first_network_alias(self) -> str:
        aliases = self._network_aliases
        if not aliases:
            raise RuntimeError(f"{type(self).__name__} has no network alias set; call with_network_aliases(...) first.")
        return aliases[0]


class LocalChainImage(enum.StrEnum):
    """Docker images available for the local subtensor chain."""

    DEFAULT = "ghcr.io/opentensor/subtensor-localnet:main"
    PREPARED_E2E = "prepared-e2e-localnet:latest"
    PREPARED_CONTACT = "prepared-contact-localnet:latest"


class LocalChainContainer(BaseDockerContainer):
    """
    Subtensor localnet container with JSON-RPC health check.

    Starts the local Bittensor chain from a Docker image and waits
    until the RPC endpoint is responsive before reporting readiness.
    """

    def __init__(
        self,
        image: LocalChainImage,
        startup_timeout: int = 30,
        *,
        host_rpc_port: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(image, **kwargs)
        self._local_chain_image = image
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
        images = docker_client.client.images.list(name=self.image)
        return len(images) > 0

    def pull_image(self) -> None:
        """
        Pull the configured Docker image to refresh the local cache.

        Used before building snapshots to avoid stale base images.
        """
        docker_client = self.get_docker_client()
        logger.info("Pulling Docker image '%s'", self.image)
        docker_client.client.images.pull(self.image)
        logger.info("Pulled Docker image '%s'", self.image)

    async def ensure_prepared_image(self) -> None:
        """
        Ensure the prepared localchain Docker image exists, building it if necessary.

        If the image is not found locally, runs a proper chain prepare script
        to create it from a fresh chain.

        Raises:
            RuntimeError: If the image cannot be prepared due to an unknown image type.
        """
        if self._prepared_image_exists():
            return
        logger.warning(
            "Docker image '%s' not found locally — building it now.",
            self.image,
        )
        if self.image == LocalChainImage.PREPARED_E2E:
            from tests.integration.localchain import prepare_e2e_chain

            prepare_fn = prepare_e2e_chain.main
        elif self.image == LocalChainImage.PREPARED_CONTACT:
            from tests.integration.localchain import prepare_contact_chain

            prepare_fn = prepare_contact_chain.main
        else:
            raise RuntimeError(f"Unable to prepare image: {self.image}")

        await prepare_fn()
        logger.info("Docker image '%s' built successfully", self.image)

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

    @property
    def internal_ws_url(self) -> str:
        return f"ws://{self.first_network_alias}:{_CHAIN_RPC_PORT}"

    @property
    def internal_http_url(self) -> str:
        return f"http://{self.first_network_alias}:{_CHAIN_RPC_PORT}"


class PylonServiceContainer(BaseDockerContainer):
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


class MitmproxyContainer(BaseDockerContainer):
    """
    Reverse-proxy mitmdump container that forwards WebSocket traffic from
    pylon_service to the localchain container and forwards every WebSocket
    frame to an HTTP recorder via the bundled addon.
    """

    def __init__(
        self,
        upstream_ws_url: str,
        startup_timeout: int = 30,
        *,
        host_recorder_port: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(_MITMPROXY_IMAGE, **kwargs)
        self._host_recorder_port = host_recorder_port if host_recorder_port is not None else find_free_port()
        self.with_bind_ports(_MITMPROXY_RECORDER_PORT, self._host_recorder_port)
        self.with_volume_mapping(str(_MITMPROXY_ADDON_PATH), "/addon.py", "ro")
        self.with_env("PYLON_WS_RECORDER_PORT", str(_MITMPROXY_RECORDER_PORT))
        self.with_command(
            [
                "mitmdump",
                "-s",
                "/addon.py",
                "--mode",
                f"reverse:{upstream_ws_url}",
                "--listen-host",
                "0.0.0.0",
                "--listen-port",
                str(_MITMPROXY_LISTEN_PORT),
                "--set",
                "websocket_message_size_limit=10485760",
            ]
        )
        self.waiting_for(
            HttpWaitStrategy(_MITMPROXY_RECORDER_PORT, "/frames")
            .with_startup_timeout(startup_timeout)
            .with_poll_interval(0.5)
        )

    @property
    def recorder_url(self) -> str:
        return f"http://{self.get_container_host_ip()}:{self._host_recorder_port}/frames"

    @property
    def internal_ws_url(self) -> str:
        return f"ws://{self.first_network_alias}:{_MITMPROXY_LISTEN_PORT}"
