import logging
from abc import ABC
from typing import Generic, TypeVar

from pylon_client._internal.client.sync.api import (
    AbstractIdentityApi,
    AbstractOpenAccessApi,
    IdentityApi,
    OpenAccessApi,
)
from pylon_client._internal.client.sync.communicators import AbstractCommunicator, HttpCommunicator
from pylon_client._internal.client.sync.config import Config

OpenAccessApiT = TypeVar("OpenAccessApiT", bound=AbstractOpenAccessApi)
IdentityApiT = TypeVar("IdentityApiT", bound=AbstractIdentityApi)
CommunicatorT = TypeVar("CommunicatorT", bound=AbstractCommunicator)
logger = logging.getLogger(__name__)


class AbstractPylonClient(Generic[OpenAccessApiT, IdentityApiT, CommunicatorT], ABC):
    """
    Base for every sync Pylon client.

    Pylon client allows easy communication with Pylon service.
    To make a request, use client's api interfaces:
      - open_access
      - identity
    Pylon client will take care of authentication and retries, you just need to construct it with proper Config
    instance.

    Example:
        with PylonClient(Config(address="127.0.0.1:8000", open_access_token="my_token")) as client:
            response = client.identity.get_latest_neurons()
    """

    _open_access_api_cls: type[OpenAccessApiT]
    _identity_api_cls: type[IdentityApiT]
    _communicator_cls: type[CommunicatorT]

    def __init__(self, config: Config):
        self.config = config
        self._open_access_communicator = self._communicator_cls(config)
        self._identity_communicator = self._communicator_cls(config)
        self.open_access = self._open_access_api_cls(self._open_access_communicator)
        self.identity = self._identity_api_cls(self._identity_communicator)
        self.is_open = False

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open(self) -> None:
        """
        Prepares the client to work by opening the communicators.

        Raises:
            ValueError: When trying to open the already opened client.
        """
        if self.is_open:
            raise ValueError("The client is already open.")
        logger.debug(f"Opening client for the server {self.config.address}")
        self.is_open = True
        self._open_access_communicator.open()
        self._identity_communicator.open()

    def close(self) -> None:
        """
        Closes the communicators.

        Raises:
            ValueError: When trying to close the already closed client.
        """
        if not self.is_open:
            raise ValueError("The client is already closed.")
        logger.debug(f"Closing client for the server {self.config.address}")
        self.is_open = False
        self._open_access_communicator.close()
        self._identity_communicator.close()


class PylonClient(AbstractPylonClient[OpenAccessApi, IdentityApi, HttpCommunicator]):
    _open_access_api_cls = OpenAccessApi
    _identity_api_cls = IdentityApi
    _communicator_cls = HttpCommunicator
