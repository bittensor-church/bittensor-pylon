import logging
import warnings
from abc import ABC
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Generic, TypeVar

import httpx

from pylon_client._internal.api._unstable.sync.api import IdentityApi as UnstableIdentityApi
from pylon_client._internal.api._unstable.sync.api import OpenAccessApi as UnstableOpenAccessApi
from pylon_client._internal.api.abstract_sync import (
    AbstractIdentityApi,
    AbstractOpenAccessApi,
)
from pylon_client._internal.api.v1.sync.api import IdentityApi, OpenAccessApi
from pylon_client._internal.client.namespace import ClientNamespace
from pylon_client._internal.client.neuron_client import SyncNeuronClientManager
from pylon_client._internal.client.sync.communicators import AbstractCommunicator, HttpCommunicator
from pylon_client._internal.client.sync.config import Config
from pylon_client._internal.pylon_commons.v1.models import Neuron
from pylon_client.exceptions import MtlsVerificationError

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
        self._neuron_client_manager = SyncNeuronClientManager(
            config.neuron_keepalive_expiry,
            config.mtls_cert_path,
            config.mtls_key_path,
            config.neurons_file,
        )

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

    @contextmanager
    def get_neuron_client(
        self,
        neuron: Neuron,
        timeout: float = 30.0,
    ) -> Iterator[httpx.Client]:
        """
        Context manager that yields a configured ``httpx.Client`` for communicating with a miner.

        The client (and its underlying connection pool) is cached by ``(ip, port)`` for the
        lifetime of this pylon client. The ``timeout`` argument only takes effect on the first
        call for a given miner; subsequent calls reuse the cached client and its baked-in timeout.

        Uses mTLS when ``mtls_cert_path``/``mtls_key_path`` are set in the client config,
        verifying the miner's certificate against the Pylon registry. Falls back
        to plain HTTP when cert/key are absent or ``neurons_file`` is set.

        Args:
            neuron: The miner to query; host, port, and hotkey are extracted from it.
            timeout: Seconds to wait for the raw TLS probe and for the yielded client's requests
                (default 30.0). Only applied on the first call for a given ``(ip, port)`` pair.

        Yields:
            httpx.Client: Configured for either plain HTTP or mTLS.

        Raises:
            MtlsVerificationError: If the miner does not present a certificate, its public
                key does not match the Pylon registry, or TLS verification fails. If raised
                from a cached client (cert rotation), the cache entry is evicted so the next
                call re-probes. Other exceptions leave the cache intact so the same client
                is reused on the next call.
            ConnectionRefusedError: If the raw TLS probe cannot connect to the miner.
            TimeoutError: If the raw TLS probe times out.

        Note:
            If two callers concurrently hold the same cached client (same neuron) and one
            raises ``MtlsVerificationError``, the client is closed immediately via
            ``invalidate``. The other caller's in-flight request on that client will fail
            with ``RuntimeError``.
        """
        ip = neuron.axon_info.ip
        port = neuron.axon_info.port
        neuron_client = self._neuron_client_manager.get(ip, port)
        if neuron_client is None:
            expected_pubkey_hex = None
            if self._neuron_client_manager.use_mtls:
                cert_resp = self.v1.identity.get_certificate(neuron.hotkey)
                expected_pubkey_hex = cert_resp.public_key
            neuron_client = self._neuron_client_manager.build_sync(ip, port, timeout, expected_pubkey_hex)
        try:
            yield neuron_client
        except MtlsVerificationError:
            self._neuron_client_manager.invalidate(ip, port, neuron_client)
            raise

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
        self._neuron_client_manager.clear()
        self._communicator.close()


class PylonClient(AbstractPylonClient[HttpCommunicator]):
    _communicator_cls = HttpCommunicator
