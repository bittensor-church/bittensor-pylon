from abc import ABC, abstractmethod
from typing import TypeVar

from bittensor_wallet import Wallet

from pylon_client._internal.common.models import BittensorModel
from pylon_client._internal.common.types import HotkeyName, NetUid

from .adapter import CacheKey

ModelT = TypeVar("ModelT", bound=BittensorModel)


class AbstractContext(ABC):
    """
    Context is an abstraction to define the params needed to fetch an object and to
    save the fetched object in that 'context' in the cache by building a cache key.

    Update tasks use the context to get necessary params to fetch the object from
    upstream network and to create a cache key for saving the object in the cache.

    RecentObjectProvider uses the context to fetch the object from the cache.
    """

    @property
    def wallet(self) -> Wallet | None:
        return None

    @abstractmethod
    def build_key(self, model: type[ModelT]) -> CacheKey[ModelT]:
        pass


class SubnetContext(AbstractContext):
    """
    Represents a context associated with a subnet.

    Use this context when caching data that is meant to be served
    by open access endpoints.
    """

    def __init__(self, netuid: NetUid):
        super().__init__()
        self.netuid = netuid

    def build_key(self, model: type[ModelT]) -> CacheKey[ModelT]:
        return CacheKey(model, self.netuid, None)

    def __str__(self) -> str:
        return f"SubnetContext(netuid={self.netuid})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, SubnetContext) and other.netuid == self.netuid


class IdentitySubnetContext(SubnetContext):
    """
    Represents a subnet context associated with an identity.

    Use this context when caching data that is meant to be served
    by identity endpoints.
    """

    def __init__(self, netuid: NetUid, wallet: Wallet):
        self._wallet = wallet
        super().__init__(netuid)

    @property
    def wallet(self) -> Wallet | None:
        return self._wallet

    def build_key(self, model: type[ModelT]) -> CacheKey[ModelT]:
        return CacheKey(model, self.netuid, HotkeyName(self._wallet.hotkey_str))

    def __str__(self) -> str:
        return f"IdentitySubnetContext(netuid={self.netuid}, wallet={self._wallet.name})"
