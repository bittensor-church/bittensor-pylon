import logging
from abc import ABC
from typing import Generic, TypeVar

from pylon_client._internal.client.asynchronous.api import (
    AbstractAsyncIdentityApi,
    AbstractAsyncOpenAccessApi,
    AsyncIdentityApi,
    AsyncOpenAccessApi,
)
from pylon_client._internal.client.asynchronous.communicators import AbstractAsyncCommunicator, AsyncHttpCommunicator
from pylon_client._internal.client.asynchronous.config import AsyncConfig

OpenAccessApiT = TypeVar("OpenAccessApiT", bound=AbstractAsyncOpenAccessApi)
IdentityApiT = TypeVar("IdentityApiT", bound=AbstractAsyncIdentityApi)
CommunicatorT = TypeVar("CommunicatorT", bound=AbstractAsyncCommunicator)
logger = logging.getLogger(__name__)


class AbstractAsyncPylonClient(Generic[OpenAccessApiT, IdentityApiT, CommunicatorT], ABC):
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

    _open_access_api_cls: type[OpenAccessApiT]
    _identity_api_cls: type[IdentityApiT]
    _communicator_cls: type[CommunicatorT]

    def __init__(self, config: AsyncConfig):
        self.config = config
        self._open_access_communicator = self._communicator_cls(config)
        self._identity_communicator = self._communicator_cls(config)
        self.open_access = self._open_access_api_cls(self._open_access_communicator)
        self.identity = self._identity_api_cls(self._identity_communicator)
        self.is_open = False

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


class AsyncPylonClient(AbstractAsyncPylonClient[AsyncOpenAccessApi, AsyncIdentityApi, AsyncHttpCommunicator]):
    _open_access_api_cls = AsyncOpenAccessApi
    _identity_api_cls = AsyncIdentityApi
    _communicator_cls = AsyncHttpCommunicator
