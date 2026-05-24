import asyncio
import logging
import ssl
import warnings
from abc import ABC
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from ipaddress import IPv6Address
from typing import Generic, TypeVar

import httpx
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.x509 import load_der_x509_certificate
from httpx import AsyncClient

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
from pylon_client._internal.pylon_commons.v1.models import Neuron
from pylon_client.exceptions import MtlsVerificationError

CommunicatorT = TypeVar("CommunicatorT", bound=AbstractAsyncCommunicator)


class _MtlsTransport(httpx.AsyncHTTPTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        try:
            return await super().handle_async_request(request)
        except httpx.ConnectError as exc:
            cause = exc.__cause__
            while cause is not None:
                if isinstance(cause, ssl.SSLError):
                    raise MtlsVerificationError(f"mTLS verification failed connecting to {request.url}") from exc
                cause = cause.__cause__
            raise


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
        self._communicator = self._communicator_cls(config)

        self.v1 = ClientNamespace(
            open_access_cls=AsyncOpenAccessApi,
            identity_cls=AsyncIdentityApi,
            communicator=self._communicator,
        )

        self.unstable = ClientNamespace(
            open_access_cls=UnstableAsyncOpenAccessApi,
            identity_cls=UnstableAsyncIdentityApi,
            communicator=self._communicator,
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

    @asynccontextmanager
    async def get_neuron_client(
        self,
        neuron: Neuron,
        timeout: float = 30.0,
    ) -> AsyncIterator[AsyncClient]:
        """
        Async context manager that yields a configured ``AsyncClient`` for communicating with a miner.

        Uses mTLS when ``mtls_cert_path``/``mtls_key_path`` are set in the client config,
        verifying the miner's certificate against the Pylon registry. Falls back
        to plain HTTP when cert/key are absent or ``neurons_file`` is set.

        Args:
            neuron: The miner to query; host, port, and hotkey are extracted from it.
            timeout: Seconds to wait for the raw TLS probe and for the yielded client's requests (default 30.0).

        Yields:
            AsyncClient: Configured for either plain HTTP or mTLS.

        Raises:
            MtlsVerificationError: If the miner does not present a certificate, its public
                key does not match the Pylon registry, or TLS verification fails.
            httpx.ConnectError: If a connection to the miner cannot be established.
        """
        ip = neuron.axon_info.ip
        host = f"[{ip}]" if isinstance(ip, IPv6Address) else str(ip)
        port = neuron.axon_info.port

        if not self.config.mtls_cert_path or not self.config.mtls_key_path or self.config.neurons_file:
            scheme = "http"
            base_url = f"{scheme}://{host}:{port}"
            async with AsyncClient(base_url=base_url, timeout=timeout) as client:
                yield client
                return

        hotkey = neuron.hotkey

        cert_resp = await self.v1.identity.get_certificate(hotkey)
        expected_pubkey_hex = cert_resp.public_key

        # Probe the miner to fetch and pin its certificate (no client cert presented here); see
        # _fetch_verified_cert_pem. verify_ctx trusts only that pinned cert.
        cert_pem = await self._fetch_verified_cert_pem(str(ip), port, expected_pubkey_hex, timeout)
        verify_ctx = self._build_pinned_ssl_context(cert_pem)
        scheme = "https"
        base_url = f"{scheme}://{host}:{port}"

        # The actual authenticated request: mutual TLS. The cert must be set on the transport (httpx
        # ignores Client(cert=...) when an explicit transport is given), so the miner can verify us,
        # while verify_ctx pins the miner's certificate so we verify it in return.
        cert = (self.config.mtls_cert_path, self.config.mtls_key_path)
        async with AsyncClient(
            transport=_MtlsTransport(verify=verify_ctx, cert=cert),
            base_url=base_url,
            timeout=timeout,
        ) as client:
            yield client
            return

    async def _fetch_verified_cert_pem(self, host: str, port: int, expected_pubkey_hex: str, timeout: float) -> str:
        """
        Opens a raw TLS connection to the miner, extracts its certificate, and verifies
        that the certificate's public key matches ``expected_pubkey_hex`` from the Pylon
        registry. Returns the certificate as a PEM string, caching it by public key hex.

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

        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port, ssl=ctx),
            timeout=timeout,
        )
        try:
            ssl_obj = writer.get_extra_info("ssl_object")
            cert_der = ssl_obj.getpeercert(binary_form=True)
            if cert_der is None:
                raise MtlsVerificationError("server did not present a certificate")

            cert = load_der_x509_certificate(cert_der)
            server_pubkey = cert.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
            if server_pubkey != expected_pubkey_hex:
                raise MtlsVerificationError("server cert public key does not match pylon registry")

            return ssl.DER_cert_to_PEM_cert(cert_der)
        finally:
            writer.close()

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
        await self._communicator.open()

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
        await self._communicator.close()


class AsyncPylonClient(AbstractAsyncPylonClient[AsyncHttpCommunicator]):
    _communicator_cls = AsyncHttpCommunicator
