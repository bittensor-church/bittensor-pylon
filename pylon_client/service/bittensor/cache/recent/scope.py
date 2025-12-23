from abc import ABC, abstractmethod
from typing import TypeVar

from bittensor_wallet import Wallet

from pylon_client._internal.common.models import BittensorModel
from pylon_client._internal.common.types import HotkeyName, NetUid

from .adapter import CacheKey

T = TypeVar("T", bound=BittensorModel)


class Scope(ABC):
    """
    Scope is an abstraction to define the params needed to fetch an object and to
    'scope' the fetched object to those params in the cache by building a cache key.

    Update tasks use the scope to get necessary params to fetch the object from
    upstream network and to create a cache key for saving the object in the cache.

    RecentObjectProvider uses the scope to fetch the object from the cache.
    """

    @property
    def wallet(self) -> Wallet | None:
        return None

    @abstractmethod
    def build_key(self, model: type[T]) -> CacheKey[T]:
        pass


class SubnetScope(Scope):
    def __init__(self, netuid: NetUid):
        super().__init__()
        self.netuid = netuid

    def build_key(self, model: type[T]) -> CacheKey[T]:
        return CacheKey(model, self.netuid, None)

    def __str__(self) -> str:
        return f"SubnetScope(netuid={self.netuid})"


class IdentitySubnetScope(SubnetScope):
    def __init__(self, netuid: NetUid, wallet: Wallet):
        self._wallet = wallet
        super().__init__(netuid)

    @property
    def wallet(self) -> Wallet | None:
        return self._wallet

    def build_key(self, model: type[T]) -> CacheKey[T]:
        return CacheKey(model, self.netuid, HotkeyName(self._wallet.hotkey_str))

    def __str__(self) -> str:
        return f"IdentitySubnetScope(netuid={self.netuid}, wallet={self._wallet.hotkey_str})"
