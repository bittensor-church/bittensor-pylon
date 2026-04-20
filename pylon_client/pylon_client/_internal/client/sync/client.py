import logging
import warnings
from abc import ABC
from typing import Generic, TypeVar

from pylon_client._internal.api._unstable.sync.api import IdentityApi as UnstableIdentityApi
from pylon_client._internal.api._unstable.sync.api import OpenAccessApi as UnstableOpenAccessApi
from pylon_client._internal.api.abstract_sync import (
    AbstractIdentityApi,
    AbstractOpenAccessApi,
)
from pylon_client._internal.api.v1.sync.api import IdentityApi, OpenAccessApi
from pylon_client._internal.client.namespace import ClientNamespace
from pylon_client._internal.client.sync.communicators import AbstractCommunicator, HttpCommunicator
from pylon_client._internal.client.sync.config import Config

CommunicatorT = TypeVar("CommunicatorT", bound=AbstractCommunicator)

logger = logging.getLogger(__name__)


class AbstractPylonClient(Generic[CommunicatorT], ABC):
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

    _communicator_cls: type[CommunicatorT]

    config: Config

    v1: ClientNamespace[OpenAccessApi, IdentityApi]
    unstable: ClientNamespace[UnstableOpenAccessApi, UnstableIdentityApi]

    def __init__(self, config: Config):
        self.config = config
        self._communicator = self._communicator_cls(config)

        self.v1 = ClientNamespace(
            open_access_cls=OpenAccessApi,
            identity_cls=IdentityApi,
            communicator=self._communicator,
        )

        self.unstable = ClientNamespace(
            open_access_cls=UnstableOpenAccessApi,
            identity_cls=UnstableIdentityApi,
            communicator=self._communicator,
        )

        self.is_open = False

    @property
    def open_access(self) -> AbstractOpenAccessApi:
        warnings.warn(
            "client.open_access is deprecated and will be removed in version 2.0.0, use client.v1.open_access instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.v1.open_access

    @property
    def identity(self) -> AbstractIdentityApi:
        warnings.warn(
            "client.identity is deprecated and will be removed in version 2.0.0, use client.v1.identity instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.v1.identity

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
        self._communicator.open()

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
        self._communicator.close()


class PylonClient(AbstractPylonClient[HttpCommunicator]):
    _communicator_cls = HttpCommunicator
