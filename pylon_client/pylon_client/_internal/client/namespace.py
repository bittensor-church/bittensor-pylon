from typing import Any, Generic, TypeVar

from pylon_client._internal.api.abstract_async import AbstractAsyncIdentityApi, AbstractAsyncOpenAccessApi
from pylon_client._internal.api.abstract_sync import AbstractIdentityApi, AbstractOpenAccessApi
from pylon_client._internal.pylon_commons.exceptions import PylonMisconfigured

OpenAccessApiT = TypeVar("OpenAccessApiT", bound=AbstractOpenAccessApi | AbstractAsyncOpenAccessApi)
IdentityApiT = TypeVar("IdentityApiT", bound=AbstractIdentityApi | AbstractAsyncIdentityApi)


class ClientNamespace(Generic[OpenAccessApiT, IdentityApiT]):
    """
    Namespace providing access to API functions.

    Acts as a factory that conditionally creates API instances based on the communicator's config.
    If the required credentials are not configured, the corresponding property raises PylonMisconfigured.
    """

    def __init__(
        self,
        open_access_cls: type[OpenAccessApiT],
        identity_cls: type[IdentityApiT],
        communicator: Any,
    ):
        config = communicator.config
        self._open_access = open_access_cls(communicator) if config.open_access_token else None
        self._identity = identity_cls(communicator) if config.identity_name else None

    @property
    def open_access(self) -> OpenAccessApiT:
        if self._open_access is None:
            raise PylonMisconfigured("Can not use open access api - no open access token provided in config.")
        return self._open_access

    @property
    def identity(self) -> IdentityApiT:
        if self._identity is None:
            raise PylonMisconfigured("Can not use identity api - no identity name or token provided in config.")
        return self._identity
