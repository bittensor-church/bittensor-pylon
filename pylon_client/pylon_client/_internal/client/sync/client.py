import logging
import socket
import ssl
import warnings
from abc import ABC
from collections.abc import Iterator
from contextlib import contextmanager
from ipaddress import IPv6Address
from typing import Generic, TypeVar

import httpx
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.x509 import load_der_x509_certificate

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
from pylon_client._internal.pylon_commons.v1.models import Neuron
from pylon_client.exceptions import MtlsVerificationError

CommunicatorT = TypeVar("CommunicatorT", bound=AbstractCommunicator)

logger = logging.getLogger(__name__)


class _MtlsTransport(httpx.HTTPTransport):
    def handle_request(self, request: httpx.Request) -> httpx.Response:
        try:
            return super().handle_request(request)
        except httpx.ConnectError as exc:
            cause = exc.__cause__
            while cause is not None:
                if isinstance(cause, ssl.SSLError):
                    raise MtlsVerificationError(f"mTLS verification failed connecting to {request.url}") from exc
                cause = cause.__cause__
            raise


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

    @contextmanager
    def get_neuron_client(
        self,
        neuron: Neuron,
        timeout: float = 30.0,
    ) -> Iterator[httpx.Client]:
        """
        Context manager that yields a configured ``httpx.Client`` for communicating with a miner.

        Uses mTLS when ``mtls_cert_path``/``mtls_key_path`` are set in the client config,
        verifying the miner's certificate against the Pylon registry. Falls back
        to plain HTTP when cert/key are absent or ``neurons_file`` is set.

        Args:
            neuron: The miner to query; host, port, and hotkey are extracted from it.
            timeout: Seconds to wait for the raw TLS probe and for the yielded client's requests (default 30.0).

        Yields:
            httpx.Client: Configured for either plain HTTP or mTLS.

        Raises:
            MtlsVerificationError: If the miner does not present a certificate, its public
                key does not match the Pylon registry, or TLS verification fails.
        """
        ip = neuron.axon_info.ip
        host = f"[{ip}]" if isinstance(ip, IPv6Address) else str(ip)
        port = neuron.axon_info.port

        if not self.config.mtls_cert_path or not self.config.mtls_key_path or self.config.neurons_file:
            scheme = "http"
            base_url = f"{scheme}://{host}:{port}"
            with httpx.Client(base_url=base_url, timeout=timeout) as client:
                yield client
            return

        hotkey = neuron.hotkey
        cert_resp = self.v1.identity.get_certificate(hotkey)
        expected_pubkey_hex = cert_resp.public_key
        # Probe the miner to fetch and pin its certificate (no client cert presented here); see
        # _fetch_verified_cert_pem. verify_ctx trusts only that pinned cert.
        cert_pem = self._fetch_verified_cert_pem(str(ip), port, expected_pubkey_hex, timeout)
        verify_ctx = self._build_pinned_ssl_context(cert_pem)

        scheme = "https"
        base_url = f"{scheme}://{host}:{port}"

        # The actual authenticated request: mutual TLS. The cert must be set on the transport (httpx
        # ignores Client(cert=...) when an explicit transport is given), so the miner can verify us,
        # while verify_ctx pins the miner's certificate so we verify it in return.
        cert = (self.config.mtls_cert_path, self.config.mtls_key_path)
        with httpx.Client(
            transport=_MtlsTransport(verify=verify_ctx, cert=cert),
            base_url=base_url,
            timeout=timeout,
        ) as client:
            yield client

    def _fetch_verified_cert_pem(self, host: str, port: int, expected_pubkey_hex: str, timeout: float) -> str:
        """
        Opens a raw TLS connection to the miner, extracts its certificate, and verifies
        that the certificate's public key matches ``expected_pubkey_hex`` from the Pylon
        registry. Returns the certificate as a PEM string.

        This is only a probe to *retrieve and pin* the miner's certificate; it is not the
        authenticated request. We deliberately:
          - present no client certificate, and
          - skip TLS verification (``CERT_NONE``), since the miner's cert is self-signed and
            is trusted via public-key pinning against the Pylon registry, not a CA chain.
        The handshake therefore succeeds without mutual auth: the miner does not require a
        client certificate to complete it, so it sends its own certificate, which is all we
        need here. The real mTLS connection (presenting our client cert and verifying against
        this pinned cert) is made afterwards by ``get_neuron_client``.

        Raises:
            MtlsVerificationError: If no certificate is presented or the public key does not match.
        """
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        sock = socket.create_connection((host, port), timeout=timeout)
        ssl_sock = ctx.wrap_socket(sock)
        try:
            cert_der = ssl_sock.getpeercert(binary_form=True)
            if cert_der is None:
                raise MtlsVerificationError("server did not present a certificate")

            cert = load_der_x509_certificate(cert_der)
            server_pubkey = cert.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
            if server_pubkey != expected_pubkey_hex:
                raise MtlsVerificationError("server cert public key does not match pylon registry")

            return ssl.DER_cert_to_PEM_cert(cert_der)
        finally:
            ssl_sock.close()

    @staticmethod
    def _build_pinned_ssl_context(cert_pem: str) -> ssl.SSLContext:
        """
        Builds an SSL context that trusts exactly the certificate in ``cert_pem`` and
        nothing else (cert pinning).
        """
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_flags |= ssl.VERIFY_X509_PARTIAL_CHAIN
        ctx.load_verify_locations(cadata=cert_pem)
        return ctx

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
