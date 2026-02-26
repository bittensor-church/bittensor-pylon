import docker.errors
import pytest
from pylon_commons.types import BittensorNetwork

from pylon_service.main import create_app
from pylon_service.settings import settings
from tests.helpers import UvicornServer, find_free_port
from tests.integration.localchain.dev_accounts import DevAccount
from tests.integration.localchain.manager import LocalChainManager

SERVICE_HOST = "localhost"
SNAPSHOT_IMAGE = "prepared-localnet:latest"


@pytest.fixture(scope="session")
def localchain():
    manager = LocalChainManager(image=SNAPSHOT_IMAGE, startup_timeout=120.0)
    try:
        try:
            manager.start()
        except docker.errors.ImageNotFound:
            pytest.exit(
                f"Docker image '{SNAPSHOT_IMAGE}' not found. "
                "Build it with: cd pylon_service && nox -s prepare-localchain",
                returncode=1,
            )
        yield manager
    finally:
        manager.stop()


@pytest.fixture(scope="session")
def pylon_service(localchain):
    settings.bittensor_network = BittensorNetwork(localchain.ws_url)
    settings.bittensor_archive_network = BittensorNetwork(localchain.ws_url)

    app = create_app()

    server = UvicornServer(app, host=SERVICE_HOST, port=find_free_port(), startup_timeout=30.0)
    server.start()
    yield server
    server.stop()


@pytest.fixture
def wallet():
    return DevAccount.ALICE.wallet


@pytest.fixture(scope="session")
def pylon_client(pylon_service):
    from pylon_client.artanis import Config, IdentityName, PylonAuthToken, PylonClient, PylonTimeout

    config = Config(
        address=f"http://{pylon_service.config.host}:{pylon_service.config.port}",
        open_access_token=PylonAuthToken("test_token"),
        identity_name=IdentityName("sn1"),
        identity_token=PylonAuthToken("sn1_token"),
        timeout=PylonTimeout(read=300),
    )
    with PylonClient(config) as client:
        yield client
