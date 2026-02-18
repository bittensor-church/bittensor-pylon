import logging
import warnings
from abc import ABC
from typing import Generic, TypeVar

from pylon_client._internal.api._unstable.asynchronous.api import AsyncIdentityApi as UnstableAsyncIdentityApi
from pylon_client._internal.api._unstable.asynchronous.api import AsyncOpenAccessApi as UnstableAsyncOpenAccessApi
from pylon_client._internal.api.abstract_async import (
    AbstractAsyncIdentityApi,
    AbstractAsyncOpenAccessApi,
)
from pylon_client._internal.api.v1.asynchronous.api import AsyncIdentityApi, AsyncOpenAccessApi
from pylon_client._internal.client.asynchronous.communicators import AbstractAsyncCommunicator, AsyncHttpCommunicator
from pylon_client._internal.client.asynchronous.config import AsyncConfig
from pylon_client._internal.client.namespace import ClientNamespace

CommunicatorT = TypeVar("CommunicatorT", bound=AbstractAsyncCommunicator)

logger = logging.getLogger(__name__)


class AbstractAsyncPylonClient(Generic[CommunicatorT], ABC):
    """
    Base for every async Pylon client.

    Pylon client allows easy communication with Pylon service.
    To make a request, use client's api interfaces:
      - open_access
      - identity
    Pylon client will take care of authentication and retries, you just need to construct it with proper AsyncConfig
    instance.

    Example:
        with AsyncPylonClient(AsyncConfig(address="127.0.0.1:8000", open_access_token="my_token")) as client:
            response = await client.identity.get_latest_neurons()
    """

    _communicator_cls: type[CommunicatorT]

    config: AsyncConfig

    v1: ClientNamespace[AsyncOpenAccessApi, AsyncIdentityApi]
    unstable: ClientNamespace[UnstableAsyncOpenAccessApi, UnstableAsyncIdentityApi]

    def __init__(self, config: AsyncConfig):
        self.config = config
        self._open_access_communicator = self._communicator_cls(config)
        self._identity_communicator = self._communicator_cls(config)

        self.v1 = ClientNamespace(
            open_access=AsyncOpenAccessApi(self._open_access_communicator),
            identity=AsyncIdentityApi(self._identity_communicator),
        )

        self.unstable = ClientNamespace(
            open_access=UnstableAsyncOpenAccessApi(self._open_access_communicator),
            identity=UnstableAsyncIdentityApi(self._identity_communicator),
        )

        self.is_open = False

    @property
    def open_access(self) -> AbstractAsyncOpenAccessApi:
        warnings.warn(
            "client.open_access is deprecated, use client.v1.open_access instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.v1.open_access

    @property
    def identity(self) -> AbstractAsyncIdentityApi:
        warnings.warn(
            "client.identity is deprecated, use client.v1.identity instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.v1.identity

    async def __aenter__(self):
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def open(self) -> None:
        """
        Prepares the client to work by opening the communicators.

        Raises:
            ValueError: When trying to open the already opened client.
        """
        if self.is_open:
            raise ValueError("The client is already open.")
        logger.debug(f"Opening client for the server {self.config.address}")
        self.is_open = True
        await self._open_access_communicator.open()
        await self._identity_communicator.open()

    async def close(self) -> None:
        """
        Closes the communicators.

        Raises:
            ValueError: When trying to close the already closed client.
        """
        if not self.is_open:
            raise ValueError("The client is already closed.")
        logger.debug(f"Closing client for the server {self.config.address}")
        self.is_open = False
        await self._open_access_communicator.close()
        await self._identity_communicator.close()


class AsyncPylonClient(AbstractAsyncPylonClient[AsyncHttpCommunicator]):
    _communicator_cls = AsyncHttpCommunicator
