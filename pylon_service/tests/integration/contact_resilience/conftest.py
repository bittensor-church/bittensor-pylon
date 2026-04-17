import subprocess
import time
from collections.abc import AsyncIterator, Iterator
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

import docker.errors
import httpx
import pytest
import pytest_asyncio
from pylon_commons.types import BittensorNetwork

from pylon_service.bittensor.contact import TurboBtContact
from tests.helpers import find_free_port
from tests.integration.contact_resilience.helpers import reset_proxy
from tests.integration.containers import LocalChainContainer, LocalChainImage
from tests.integration.localchain.manager import DockerContextEndpoint, LocalChainManager

TOXIPROXY_IMAGE = "ghcr.io/shopify/toxiproxy:2.12.0"
TOXIPROXY_API_PORT = 8474
TOXIPROXY_LISTEN_PORT = 9945


@dataclass(frozen=True)
class ToxiProxyHandle:
    name: str
    listen: str
    upstream: str
    control_url: str


@dataclass(frozen=True)
class ToxiProxyRuntime:
    container: Any
    control_host: str
    api_port: int
    listen_port: int


@pytest_asyncio.fixture(scope="package")
async def resilience_chain() -> AsyncIterator[LocalChainManager]:
    container = LocalChainContainer(image=LocalChainImage.PREPARED_CONTACT)
    await container.ensure_prepared_image()
    manager = LocalChainManager(container)
    try:
        await manager.start()
        yield manager
    finally:
        await manager.stop()


@pytest_asyncio.fixture
async def live_contact(resilience_chain: LocalChainManager):
    async with TurboBtContact(wallet=None, uri=BittensorNetwork(resilience_chain.ws_url)) as contact:
        yield contact


@pytest.fixture(scope="package")
def docker_context() -> DockerContextEndpoint:
    return LocalChainManager.load_active_docker_context()


@pytest.fixture(scope="package")
def toxiproxy_docker_client(docker_context: DockerContextEndpoint):
    return LocalChainManager.docker_client_for_context(docker_context)


def _start_ssh_tunnel(
    container,
    *,
    docker_context: DockerContextEndpoint,
    local_port: int,
    remote_port: int,
) -> subprocess.Popen[str]:
    container_ip = LocalChainManager.get_container_ip(container)
    if docker_context.hostname is None:
        raise RuntimeError(f"SSH docker context {docker_context.raw_host!r} is missing a host")
    remote = (
        f"{docker_context.username}@{docker_context.hostname}" if docker_context.username else docker_context.hostname
    )
    command = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ExitOnForwardFailure=yes",
        "-N",
        "-L",
        f"{local_port}:{container_ip}:{remote_port}",
    ]
    if docker_context.port is not None:
        command.extend(["-p", str(docker_context.port)])
    command.append(remote)
    return subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)


def _stop_ssh_tunnel(process: subprocess.Popen[str] | None) -> None:
    if process is None:
        return
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def _get_published_host_port(container, container_port: int) -> int:
    container.reload()
    ports = container.attrs.get("NetworkSettings", {}).get("Ports", {})
    bindings = ports.get(f"{container_port}/tcp")
    if not bindings:
        raise RuntimeError(f"Docker did not publish port {container_port} for toxiproxy")
    host_port = bindings[0].get("HostPort")
    if not host_port:
        raise RuntimeError(f"Docker did not report a host port for toxiproxy port {container_port}")
    return int(host_port)


@pytest.fixture(scope="package")
def toxiproxy_runtime(toxiproxy_docker_client, docker_context: DockerContextEndpoint) -> Iterator[ToxiProxyRuntime]:
    control_host = LocalChainManager.resolve_rpc_host_for_context(docker_context)
    ports = None
    api_local_port: int | None = None
    listen_local_port: int | None = None
    if docker_context.scheme == "ssh":
        api_local_port = find_free_port()
        listen_local_port = find_free_port()
    else:
        ports = {
            f"{TOXIPROXY_API_PORT}/tcp": None,
            f"{TOXIPROXY_LISTEN_PORT}/tcp": None,
        }
    run_kwargs: dict[str, object] = {
        "detach": True,
        "remove": True,
        "name": f"pylon-toxiproxy-{time.time_ns()}",
    }
    if ports is not None:
        run_kwargs["ports"] = ports
    container = None
    api_tunnel: subprocess.Popen[str] | None = None
    listen_tunnel: subprocess.Popen[str] | None = None
    try:
        container = toxiproxy_docker_client.containers.run(TOXIPROXY_IMAGE, **run_kwargs)
        if docker_context.scheme == "ssh":
            assert api_local_port is not None
            assert listen_local_port is not None
            api_tunnel = _start_ssh_tunnel(
                container,
                docker_context=docker_context,
                local_port=api_local_port,
                remote_port=TOXIPROXY_API_PORT,
            )
            listen_tunnel = _start_ssh_tunnel(
                container,
                docker_context=docker_context,
                local_port=listen_local_port,
                remote_port=TOXIPROXY_LISTEN_PORT,
            )
            api_port = api_local_port
            listen_port = listen_local_port
        else:
            api_port = _get_published_host_port(container, TOXIPROXY_API_PORT)
            listen_port = _get_published_host_port(container, TOXIPROXY_LISTEN_PORT)
        deadline = time.monotonic() + 15.0
        control_url = f"http://{control_host}:{api_port}"
        while time.monotonic() < deadline:
            with suppress(httpx.HTTPError):
                response = httpx.get(f"{control_url}/version", timeout=1.0)
                if response.status_code == 200:
                    break
            time.sleep(0.2)
        else:
            raise RuntimeError("toxiproxy API did not become ready")
        yield ToxiProxyRuntime(
            container=container,
            control_host=control_host,
            api_port=api_port,
            listen_port=listen_port,
        )
    finally:
        _stop_ssh_tunnel(api_tunnel)
        _stop_ssh_tunnel(listen_tunnel)
        if container is not None:
            with suppress(docker.errors.NotFound):
                container.remove(force=True)


@pytest.fixture
def toxiproxy_handle(
    toxiproxy_runtime: ToxiProxyRuntime,
    resilience_chain: LocalChainManager,
) -> Iterator[ToxiProxyHandle]:
    chain_container = resilience_chain.get_container()
    upstream = f"{LocalChainManager.get_container_ip(chain_container)}:9944"
    control_url = f"http://{toxiproxy_runtime.control_host}:{toxiproxy_runtime.api_port}"
    payload = {
        "name": "subtensor",
        "listen": f"0.0.0.0:{TOXIPROXY_LISTEN_PORT}",
        "upstream": upstream,
    }
    response = httpx.post(f"{control_url}/proxies", json=payload, timeout=5.0)
    if response.status_code == 409:
        httpx.delete(f"{control_url}/proxies/subtensor", timeout=5.0)
        response = httpx.post(f"{control_url}/proxies", json=payload, timeout=5.0)
    response.raise_for_status()
    try:
        yield ToxiProxyHandle(
            name="subtensor",
            listen=f"ws://{toxiproxy_runtime.control_host}:{toxiproxy_runtime.listen_port}",
            upstream=upstream,
            control_url=control_url,
        )
    finally:
        with suppress(httpx.HTTPError):
            httpx.delete(f"{control_url}/proxies/subtensor", timeout=5.0)


@pytest_asyncio.fixture
async def proxied_contact(toxiproxy_handle: ToxiProxyHandle):
    async with TurboBtContact(wallet=None, uri=BittensorNetwork(toxiproxy_handle.listen)) as contact:
        try:
            yield contact
        finally:
            reset_proxy(toxiproxy_handle.name, toxiproxy_handle.control_url)
