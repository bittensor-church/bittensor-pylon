import os
import logging
import subprocess
from urllib.parse import urlparse

from testcontainers.core.config import testcontainers_config


logger = logging.getLogger(__name__)


def _get_docker_host_from_context() -> str | None:
    try:
        result = subprocess.run(
            ["docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        logger.info("Failed to get docker host from docker context, using the default.", exc_info=True)
    return None


def configure_testcontainers() -> None:
    docker_host = _get_docker_host_from_context()
    if docker_host:
        os.environ["DOCKER_HOST"] = docker_host

        parsed = urlparse(docker_host)
        if parsed.scheme == "ssh" and parsed.hostname:
            testcontainers_config.tc_host_override = parsed.hostname

    testcontainers_config.ryuk_disabled = True


configure_testcontainers()
