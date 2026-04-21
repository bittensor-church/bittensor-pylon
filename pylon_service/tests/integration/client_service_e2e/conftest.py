import logging
import os
from contextlib import contextmanager
from pathlib import Path

import bittensor_drand
import pytest
import pytest_asyncio
from pylon_client.artanis import Config, IdentityName, PylonAuthToken, PylonClient, PylonTimeout
from testcontainers.core.network import Network

from tests.integration.containers import LocalChainContainer, PylonServiceContainer
from tests.integration.localchain.dev_accounts import DevAccount
from tests.integration.localchain.manager import LocalChainManager

logger = logging.getLogger(__name__)

_WALLETS_PATH = os.environ.get("PYLON_TEST_WALLETS_PATH", Path(__file__).resolve().parents[2] / "wallets")


@pytest.fixture(scope="package")
def docker_network():
    with Network() as network:
        yield network


@pytest.fixture(scope="package")
def pylon_service_image():
    image = PylonServiceContainer.build_image()
    yield image


@pytest_asyncio.fixture(scope="package")
async def localchain(docker_network):
    container = (
        LocalChainContainer()
        .with_network(docker_network)
        .with_network_aliases("localchain")
        .with_env("RUST_LOG", "pallet_drand=debug,sc_offchain=debug")
    )
    await container.ensure_prepared_image()
    async with LocalChainManager(container) as manager:
        # Phase 2 of drand workaround — see localchain/README.md#drand-workaround
        latest_round = bittensor_drand.get_latest_round()
        logger.info("Setting Drand.LastStoredRound to %d on localchain", latest_round)
        await manager.set_drand_last_stored_round(DevAccount.ALICE.wallet, latest_round)
        await manager.set_drand_oldest_stored_round(DevAccount.ALICE.wallet, latest_round)
        yield manager


@pytest.fixture(scope="package")
def pylon_service(docker_network, localchain, pylon_service_image):
    docker_host = os.environ.get("DOCKER_HOST")
    if docker_host and docker_host.startswith("ssh://"):
        logger.warning(
            "You are using docker via ssh. Make sure the test wallets are mounted properly, "
            "otherwise the tests might fail. You may achieve this by copying test wallets to the remote host and "
            "setting PYLON_TEST_WALLETS_PATH environment variable on the host machine."
        )
    with PylonServiceContainer(
        image=str(pylon_service_image),
        chain_url="ws://localchain:9944",
        wallets_path=str(_WALLETS_PATH),
    ).with_network(docker_network) as container:
        yield container


@pytest.fixture(scope="package")
def pylon_client_factory(pylon_service):
    @contextmanager
    def _factory(identity_name: str):
        config = Config(
            address=pylon_service.api_url,
            open_access_token=PylonAuthToken("test_token"),
            identity_name=IdentityName(identity_name),
            identity_token=PylonAuthToken(f"{identity_name}_token"),
            timeout=PylonTimeout(read=300),
        )
        with PylonClient(config) as client:
            yield client

    return _factory
