import docker.errors
import pytest
import pytest_asyncio
from pylon_commons.types import BittensorNetwork, NetUid

from pylon_service.bittensor.contact import TurboBtContact
from tests.integration.localchain.dev_accounts import DevAccount
from tests.integration.localchain.manager import LocalChainManager

READ_SNAPSHOT_IMAGE = "prepared-localnet:latest"


@pytest.fixture(scope="module")
def read_chain():
    manager = LocalChainManager(image=READ_SNAPSHOT_IMAGE, startup_timeout=120.0)
    try:
        manager.start()
    except docker.errors.ImageNotFound as exc:
        raise pytest.UsageError(f"Docker image '{READ_SNAPSHOT_IMAGE}' not found") from exc

    try:
        yield manager
    finally:
        manager.stop()


@pytest_asyncio.fixture
async def open_contact(read_chain: LocalChainManager):
    async with TurboBtContact(wallet=None, uri=BittensorNetwork(read_chain.ws_url)) as contact:
        yield contact


@pytest.fixture(scope="module")
def prepared_netuid() -> NetUid:
    return NetUid(1)


@pytest.fixture(scope="module")
def write_chain():
    manager = LocalChainManager(startup_timeout=120.0)
    try:
        manager.start()
    except docker.errors.ImageNotFound as exc:
        raise pytest.UsageError(f"Docker image '{LocalChainManager.IMAGE}' not found") from exc

    try:
        yield manager
    finally:
        manager.stop()


@pytest_asyncio.fixture(scope="module")
async def write_subnets(write_chain: LocalChainManager) -> tuple[NetUid, NetUid]:
    direct_netuid, commit_netuid = await write_chain.prepare_contact_write_subnets(
        sudo_wallet=DevAccount.ALICE.wallet,
        participant_wallets=[DevAccount.ALICE.wallet, DevAccount.BOB.wallet],
    )
    return NetUid(direct_netuid), NetUid(commit_netuid)


@pytest.fixture(scope="module")
def direct_netuid(write_subnets: tuple[NetUid, NetUid]) -> NetUid:
    return write_subnets[0]


@pytest.fixture(scope="module")
def commit_netuid(write_subnets: tuple[NetUid, NetUid]) -> NetUid:
    return write_subnets[1]


@pytest_asyncio.fixture
async def write_contact(write_chain: LocalChainManager):
    async with TurboBtContact(wallet=DevAccount.ALICE.wallet, uri=BittensorNetwork(write_chain.ws_url)) as contact:
        yield contact
