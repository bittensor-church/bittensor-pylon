import pytest
from pylon_commons.models import BittensorModel
from pylon_commons.types import HotkeyName, NetUid

from pylon_service.bittensor.recent import IdentitySubnetContext, SubnetContext
from pylon_service.bittensor.recent.adapter import CacheKey


@pytest.fixture
def subnet_context() -> SubnetContext:
    return SubnetContext(NetUid(1))


@pytest.fixture
def identity_subnet_context(wallet) -> IdentitySubnetContext:
    return IdentitySubnetContext(NetUid(1), wallet)


def test_subnet_context_cache_key(subnet_context):
    assert subnet_context.build_key(BittensorModel) == CacheKey(BittensorModel, subnet_context.netuid, None)


def test_identity_subnet_context_cache_key(identity_subnet_context, wallet):
    assert identity_subnet_context.build_key(BittensorModel) == CacheKey(
        BittensorModel, identity_subnet_context.netuid, HotkeyName(wallet.hotkey_str)
    )
