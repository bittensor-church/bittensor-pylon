import asyncio
import logging
import socket
import ssl
import threading
from collections import OrderedDict
from ipaddress import IPv4Address, IPv6Address
from typing import Generic, TypeVar

import httpx
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.x509 import load_der_x509_certificate

from pylon_client._internal.pylon_commons.types import Port
from pylon_client.exceptions import MtlsVerificationError

logger = logging.getLogger(__name__)

# Bittensor caps subnets at 256 neurons; one extra slot prevents eviction when all are active.
NEURON_CLIENT_CACHE_SIZE = 257

ClientT = TypeVar("ClientT", httpx.Client, httpx.AsyncClient)


def format_neuron_host(ip: IPv4Address | IPv6Address) -> str:
    """
    Format an IP address as a URL host segment, wrapping IPv6 addresses in brackets.
    """
    return f"[{ip}]" if isinstance(ip, IPv6Address) else str(ip)


def _make_probe_ssl_context() -> ssl.SSLContext:
    """
    Create a TLS context that accepts any server certificate without verification.
    Used exclusively for the cert-pinning probe, where we read the cert before deciding to trust it.
    """
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _verify_cert_der(cert_der: bytes | None, expected_pubkey_hex: str) -> str:
    """
    Verify that the DER-encoded certificate's public key matches ``expected_pubkey_hex``.
    Returns the certificate as a PEM string for use in a pinned SSL context.

    Raises:
        MtlsVerificationError: If no certificate was presented or the public key does not match.
    """
    if cert_der is None:
        raise MtlsVerificationError("server did not present a certificate")
    cert = load_der_x509_certificate(cert_der)
    server_pubkey = cert.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    if server_pubkey != expected_pubkey_hex:
        raise MtlsVerificationError("server cert public key does not match pylon registry")
    return ssl.DER_cert_to_PEM_cert(cert_der)


def _raise_as_mtls_if_ssl(exc: httpx.ConnectError, url: object) -> None:
    """
    Re-raise ``exc`` as ``MtlsVerificationError`` if its cause chain contains an ``ssl.SSLError``.
    Called from mTLS transport wrappers to surface TLS failures as a typed exception.

    Raises:
        MtlsVerificationError: If the exception chain contains an ``ssl.SSLError``.
    """
    cause = exc.__cause__
    while cause is not None:
        if isinstance(cause, ssl.SSLError):
            raise MtlsVerificationError(f"mTLS verification failed connecting to {url}") from exc
        cause = cause.__cause__


class _MtlsSyncTransport(httpx.HTTPTransport):
    def handle_request(self, request: httpx.Request) -> httpx.Response:
        try:
            return super().handle_request(request)
        except httpx.ConnectError as exc:
            _raise_as_mtls_if_ssl(exc, request.url)
            raise


class _MtlsAsyncTransport(httpx.AsyncHTTPTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        try:
            return await super().handle_async_request(request)
        except httpx.ConnectError as exc:
            _raise_as_mtls_if_ssl(exc, request.url)
            raise


class BaseNeuronClientManager(Generic[ClientT]):
    """
    Common state and helpers for neuron client management. Not instantiated directly.

    Owns the LRU cache structure and all operations that don't require locking: client
    construction, TLS probing, cert pinning, cache get/insert, and invalidation. Subclasses
    add the appropriate lock (threading or asyncio) and expose the build and clear methods.
    """

    use_mtls: bool

    def __init__(
        self,
        keepalive_expiry: float,
        mtls_cert_path: str | None,
        mtls_key_path: str | None,
        neurons_file: str | None,
    ) -> None:
        self._limits = httpx.Limits(keepalive_expiry=keepalive_expiry)
        self.use_mtls = bool(mtls_cert_path) and bool(mtls_key_path) and not bool(neurons_file)
        self._cert: tuple[str, str] | None = (
            (mtls_cert_path, mtls_key_path) if mtls_cert_path and mtls_key_path else None
        )
        self._client_lru: OrderedDict[tuple[IPv4Address | IPv6Address, Port], ClientT] = OrderedDict()

    def get(self, ip: IPv4Address | IPv6Address, port: Port) -> ClientT | None:
        """Return cached client (LRU touch) or None on miss."""
        key = (ip, port)
        if key not in self._client_lru:
            return None
        self._client_lru.move_to_end(key)
        return self._client_lru[key]

    def _cache_insert(self, key: tuple[IPv4Address | IPv6Address, Port], client: ClientT) -> ClientT | None:
        """Insert client; return the evicted LRU entry (caller must close) or None."""
        self._client_lru[key] = client
        if len(self._client_lru) > NEURON_CLIENT_CACHE_SIZE:
            return self._client_lru.popitem(last=False)[1]
        return None

    def _make_sync_client(self, host: str, port: int, timeout: float, cert_pem: str | None = None) -> httpx.Client:
        if cert_pem is None:
            return httpx.Client(base_url=f"http://{host}:{port}", timeout=timeout, limits=self._limits)
        verify_ctx = self._build_pinned_ssl_context(cert_pem)
        assert self._cert is not None
        return httpx.Client(
            transport=_MtlsSyncTransport(verify=verify_ctx, cert=self._cert),
            base_url=f"https://{host}:{port}",
            timeout=timeout,
            limits=self._limits,
        )

    def _make_async_client(
        self, host: str, port: int, timeout: float, cert_pem: str | None = None
    ) -> httpx.AsyncClient:
        if cert_pem is None:
            return httpx.AsyncClient(base_url=f"http://{host}:{port}", timeout=timeout, limits=self._limits)
        verify_ctx = self._build_pinned_ssl_context(cert_pem)
        assert self._cert is not None
        return httpx.AsyncClient(
            transport=_MtlsAsyncTransport(verify=verify_ctx, cert=self._cert),
            base_url=f"https://{host}:{port}",
            timeout=timeout,
            limits=self._limits,
        )

    def _probe_cert_sync(self, host: str, port: int, expected_pubkey_hex: str, timeout: float) -> str:
        """
        Open a raw TLS connection purely to read the certificate the server presents.
        We don't send any HTTP request — the connection succeeding is not the goal;
        getting the peer cert for public-key pinning is.
        """
        ctx = _make_probe_ssl_context()
        sock = socket.create_connection((host, port), timeout=timeout)
        ssl_sock = ctx.wrap_socket(sock)
        try:
            return _verify_cert_der(ssl_sock.getpeercert(binary_form=True), expected_pubkey_hex)
        finally:
            ssl_sock.close()

    async def _probe_cert_async(self, host: str, port: int, expected_pubkey_hex: str, timeout: float) -> str:
        """
        Open a raw TLS connection purely to read the certificate the server presents.
        We don't send any HTTP request — the connection succeeding is not the goal;
        getting the peer cert for public-key pinning is.
        """
        ctx = _make_probe_ssl_context()
        _reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port, ssl=ctx),
            timeout=timeout,
        )
        try:
            ssl_obj = writer.get_extra_info("ssl_object")
            return _verify_cert_der(ssl_obj.getpeercert(binary_form=True), expected_pubkey_hex)
        finally:
            writer.close()

    @staticmethod
    def _build_pinned_ssl_context(cert_pem: str) -> ssl.SSLContext:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_flags |= ssl.VERIFY_X509_PARTIAL_CHAIN
        ctx.load_verify_locations(cadata=cert_pem)
        return ctx


class SyncNeuronClientManager(BaseNeuronClientManager[httpx.Client]):
    """
    Thread-safe neuron client manager for synchronous (httpx.Client) use.

    Uses ``threading.Lock`` to guard all cache mutations. The TLS probe in ``build_sync``
    runs outside the lock (slow IO); the cache check-and-insert is atomic inside the lock.
    """

    def __init__(
        self,
        keepalive_expiry: float,
        mtls_cert_path: str | None,
        mtls_key_path: str | None,
        neurons_file: str | None,
    ) -> None:
        super().__init__(keepalive_expiry, mtls_cert_path, mtls_key_path, neurons_file)
        self._lock = threading.Lock()

    def clear(self) -> None:
        """Close and remove all cached clients."""
        with self._lock:
            clients = list(self._client_lru.values())
            self._client_lru.clear()
        for c in clients:
            c.close()

    def invalidate(self, ip: IPv4Address | IPv6Address, port: Port, client: httpx.Client) -> None:
        """
        Close ``client`` and remove it from cache if it is still the cached entry for ``(ip, port)``.

        We compare by identity rather than key alone because multiple threads may all concurrently
        hold the same cached client and raise ``MtlsVerificationError``. The first caller evicts
        and closes the stale client; subsequent callers find a fresh client at the same key and
        must not evict it.
        """
        with self._lock:
            if self._client_lru.get((ip, port)) is not client:
                return
            self._client_lru.pop((ip, port))
        client.close()

    def build_sync(
        self,
        ip: IPv4Address | IPv6Address,
        port: Port,
        timeout: float,
        expected_pubkey_hex: str | None = None,
    ) -> httpx.Client:
        """
        Build a sync httpx client for ``(ip, port)``, store in cache, and return it.

        If ``expected_pubkey_hex`` is provided, probes the miner's TLS cert and pins it (mTLS);
        otherwise returns a plain HTTP client. Evicts and closes the LRU entry if the cache is full.
        The probe runs outside the lock; the cache check-and-insert is atomic inside the lock.

        Raises:
            MtlsVerificationError: If the server does not present a certificate or its public key
                does not match ``expected_pubkey_hex``.
            ConnectionRefusedError: If the raw TLS probe cannot connect to the miner.
            TimeoutError: If the raw TLS probe times out.
        """
        cert_pem: str | None = None
        if expected_pubkey_hex is not None:
            cert_pem = self._probe_cert_sync(str(ip), port, expected_pubkey_hex, timeout)

        # Lock ensures the cache check and insert are atomic: two threads trying to build
        # a client concurrently will both reach here, but only the first builds the client.
        with self._lock:
            existing = self.get(ip, port)
            if existing is not None:
                return existing
            client = self._make_sync_client(format_neuron_host(ip), port, timeout, cert_pem)
            evicted = self._cache_insert((ip, port), client)

        if evicted is not None:
            evicted.close()
        return client


class AsyncNeuronClientManager(BaseNeuronClientManager[httpx.AsyncClient]):
    """
    Coroutine-safe neuron client manager for asynchronous (httpx.AsyncClient) use.

    Uses ``asyncio.Lock`` to guard the cache check-and-insert in ``build_async`` and the
    snapshot-and-clear in ``aclear``. ``get`` and ``invalidate`` need no lock because they
    contain no ``await`` — the asyncio event loop is single-threaded and won't context-switch
    mid-operation.
    """

    def __init__(
        self,
        keepalive_expiry: float,
        mtls_cert_path: str | None,
        mtls_key_path: str | None,
        neurons_file: str | None,
    ) -> None:
        super().__init__(keepalive_expiry, mtls_cert_path, mtls_key_path, neurons_file)
        self._lock = asyncio.Lock()

    async def aclear(self) -> None:
        """Close and remove all cached clients concurrently."""
        async with self._lock:
            clients = list(self._client_lru.values())
            self._client_lru.clear()
        await asyncio.gather(*[c.aclose() for c in clients])

    async def invalidate(self, ip: IPv4Address | IPv6Address, port: Port, client: httpx.AsyncClient) -> None:
        """
        Close ``client`` and remove it from cache if it is still the cached entry for ``(ip, port)``.

        We compare by identity rather than key alone because multiple coroutines may all concurrently
        hold the same cached client and raise ``MtlsVerificationError``. The first caller evicts
        and closes the stale client; subsequent callers find a fresh client at the same key and
        must not evict it. No lock is needed: the check and pop contain no ``await``, so the event
        loop cannot switch between them.
        """
        if self._client_lru.get((ip, port)) is not client:
            return
        await self._client_lru.pop((ip, port)).aclose()

    async def build_async(
        self,
        ip: IPv4Address | IPv6Address,
        port: Port,
        timeout: float,
        expected_pubkey_hex: str | None = None,
    ) -> httpx.AsyncClient:
        """
        Build an async httpx client for ``(ip, port)``, store in cache, and return it.

        If ``expected_pubkey_hex`` is provided, probes the miner's TLS cert and pins it (mTLS);
        otherwise returns a plain HTTP client. The probe runs outside the lock (it yields to the
        event loop); the cache check-and-insert is atomic inside the lock, preventing two concurrent
        coroutines from each building a client for the same miner.

        Raises:
            MtlsVerificationError: If the server does not present a certificate or its public key
                does not match ``expected_pubkey_hex``.
            ConnectionRefusedError: If the raw TLS probe cannot connect to the miner.
            TimeoutError: If the raw TLS probe times out.
        """
        cert_pem: str | None = None
        if expected_pubkey_hex is not None:
            cert_pem = await self._probe_cert_async(str(ip), port, expected_pubkey_hex, timeout)

        # Lock ensures the cache check and insert are atomic: two coroutines trying to build
        # a client concurrently will both reach here, but only the first builds the client.
        async with self._lock:
            existing = self.get(ip, port)
            if existing is not None:
                return existing
            async_client = self._make_async_client(format_neuron_host(ip), port, timeout, cert_pem)
            evicted = self._cache_insert((ip, port), async_client)

        if evicted is not None:
            await evicted.aclose()
        return async_client
