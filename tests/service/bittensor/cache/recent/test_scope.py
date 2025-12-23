import pytest

from pylon_client._internal.common.models import BittensorModel
from pylon_client._internal.common.types import HotkeyName, NetUid
from pylon_client.service.bittensor.cache.recent.adapter import CacheKey
from pylon_client.service.bittensor.cache.recent.scope import IdentitySubnetScope, SubnetScope


@pytest.fixture
def subnet_scope() -> SubnetScope:
    return SubnetScope(NetUid(1))


@pytest.fixture
def identity_subnet_scope(wallet) -> IdentitySubnetScope:
    return IdentitySubnetScope(NetUid(1), wallet)


def test_subnet_scope_cache_key(subnet_scope):
    assert subnet_scope.build_key(BittensorModel) == CacheKey(BittensorModel, subnet_scope.netuid, None)


def test_identity_subnet_scope_cache_key(identity_subnet_scope, wallet):
    assert identity_subnet_scope.build_key(BittensorModel) == CacheKey(
        BittensorModel, identity_subnet_scope.netuid, HotkeyName(wallet.hotkey_str)
    )
