from typing import Generic, TypeVar

from pylon_client._internal.api.abstract_async import AbstractAsyncIdentityApi, AbstractAsyncOpenAccessApi
from pylon_client._internal.api.abstract_sync import AbstractIdentityApi, AbstractOpenAccessApi

OpenAccessApiT = TypeVar("OpenAccessApiT", bound=AbstractOpenAccessApi | AbstractAsyncOpenAccessApi)
IdentityApiT = TypeVar("IdentityApiT", bound=AbstractIdentityApi | AbstractAsyncIdentityApi)


class ClientNamespace(Generic[OpenAccessApiT, IdentityApiT]):
    """
    Namespace providing access to API functions.
    """

    open_access: OpenAccessApiT
    identity: IdentityApiT

    def __init__(self, open_access: OpenAccessApiT, identity: IdentityApiT):
        self.open_access = open_access
        self.identity = identity
