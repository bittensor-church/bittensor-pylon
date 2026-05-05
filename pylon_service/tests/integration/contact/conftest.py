from __future__ import annotations

from dataclasses import dataclass

import pytest
import pytest_asyncio
from pylon_commons.types import BittensorNetwork, NetUid

from pylon_service.bittensor.contact import TurboBtContact
from tests.integration.containers import LocalChainContainer, LocalChainImage
from tests.integration.localchain.dev_accounts import DevAccount
from tests.integration.localchain.manager import LocalChainManager
from tests.integration.localchain.prepare_contact_chain import SUBNET_CONFIGS


@dataclass
class PreparedSubnet:
    use_commit_reveal: bool
    use_mechanisms: bool
    netuid: NetUid


@pytest_asyncio.fixture(scope="module")
async def contact_chain():
    container = LocalChainContainer(image=LocalChainImage.PREPARED_CONTACT)
    await container.ensure_prepared_image()
    manager = LocalChainManager(container)
    await manager.start()
    # Phase 2 of drand workaround — see localchain/README.md#drand-workaround
    await manager.synchronize_drand_last_stored_round()
    try:
        yield manager
    finally:
        await manager.stop()


@pytest_asyncio.fixture
async def open_contact(contact_chain: LocalChainManager):
    async with TurboBtContact(wallet=None, uri=BittensorNetwork(contact_chain.ws_url)) as contact:
        yield contact


@pytest_asyncio.fixture
async def write_contact(contact_chain: LocalChainManager):
    async with TurboBtContact(wallet=DevAccount.ALICE.wallet, uri=BittensorNetwork(contact_chain.ws_url)) as contact:
        yield contact


@pytest_asyncio.fixture
async def turbobt_client(open_contact: TurboBtContact):
    return await open_contact._get_bt_client()


@pytest.fixture(scope="module")
async def prepared_subnets(contact_chain: LocalChainManager) -> list[PreparedSubnet]:
    start_netuid = await contact_chain.get_total_networks() - len(SUBNET_CONFIGS)
    prepared_subnets: list[PreparedSubnet] = []

    for offset, subnet_config in enumerate(SUBNET_CONFIGS):
        prepared_subnets.append(
            PreparedSubnet(
                netuid=NetUid(start_netuid + offset),
                use_commit_reveal=subnet_config.use_commit_reveal,
                use_mechanisms=subnet_config.use_mechanisms,
            )
        )

    return prepared_subnets


@pytest.fixture
def participant_uids_factory():
    async def factory(contact: TurboBtContact, netuid: NetUid) -> dict[DevAccount, int]:
        latest_block = await contact.get_latest_block()
        neurons = await contact.get_neurons_list(netuid, latest_block)
        return dict(
            [
                (dev_account, next(neuron.uid for neuron in neurons if neuron.hotkey == dev_account.hotkey_ss58))
                for dev_account in DevAccount
            ]
        )

    return factory


@pytest.fixture(scope="module")
def direct_netuid(prepared_subnets: list[PreparedSubnet]) -> NetUid:
    direct_subnets = [
        subnet for subnet in prepared_subnets if not subnet.use_commit_reveal and not subnet.use_mechanisms
    ]
    return direct_subnets[0].netuid


@pytest.fixture(scope="module")
def commit_netuid(prepared_subnets: list[PreparedSubnet]) -> NetUid:
    commit_subnets = [subnet for subnet in prepared_subnets if subnet.use_commit_reveal and not subnet.use_mechanisms]
    return commit_subnets[0].netuid


@pytest.fixture(scope="module")
def mechanism_direct_netuid(prepared_subnets: list[PreparedSubnet]) -> NetUid:
    direct_subnets = [subnet for subnet in prepared_subnets if not subnet.use_commit_reveal and subnet.use_mechanisms]
    return direct_subnets[0].netuid


@pytest.fixture(scope="module")
def mechanism_commit_netuid(prepared_subnets: list[PreparedSubnet]) -> NetUid:
    commit_subnets = [subnet for subnet in prepared_subnets if subnet.use_commit_reveal and subnet.use_mechanisms]
    return commit_subnets[0].netuid


@pytest.fixture(scope="module")
def prepared_netuid() -> NetUid:
    return NetUid(2)
