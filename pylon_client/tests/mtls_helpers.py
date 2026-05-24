"""
Helpers for exercising `get_neuron_client` against a real TLS server, so tests can prove the client
actually performs an mTLS (or plain HTTP) connection rather than just returning the right object type.
"""

import datetime
import ssl
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from cryptography.x509.oid import NameOID


def generate_ed25519_cert(common_name: str, cert_path: Path, key_path: Path) -> str:
    """
    Generates a self-signed Ed25519 certificate/key pair, writes them as PEM to the given paths, and
    returns the raw public key as hex (the form Pylon stores and the client pins against).
    """
    key = Ed25519PrivateKey.generate()
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = datetime.datetime.now(datetime.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .sign(key, None)
    )
    cert_path.write_bytes(cert.public_bytes(Encoding.PEM))
    key_path.write_bytes(key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()))
    return key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()


class _RecordingHandler(BaseHTTPRequestHandler):
    """
    Responds 200 to any GET and records the peer (client) certificate, if any, so the test can assert
    whether the connecting client presented a certificate (i.e. whether mTLS actually happened).
    """

    def do_GET(self) -> None:
        try:
            self.server.client_cert_der = self.connection.getpeercert(binary_form=True)  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            self.server.client_cert_der = None  # type: ignore[attr-defined]
        body = b"ok"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:  # silence per-request logging
        pass


class _QuietServer(ThreadingHTTPServer):
    """
    A threaded HTTP server that swallows connection errors (e.g. the client's raw cert-probe connection
    closing mid-handshake) so they don't spam stderr or fail the test.
    """

    daemon_threads = True
    client_cert_der: bytes | None = None

    def handle_error(self, request: object, client_address: object) -> None:
        pass


@contextmanager
def mtls_server(server_cert: Path, server_key: Path, trusted_client_cert: Path) -> Iterator[_QuietServer]:
    """
    Runs a TLS server that presents `server_cert` and requests (but does not require) a client cert,
    trusting `trusted_client_cert`. Client auth is optional so the client's initial cert-probe
    connection (which sends no client cert) can still complete its handshake.
    """
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(certfile=str(server_cert), keyfile=str(server_key))
    ctx.verify_mode = ssl.CERT_OPTIONAL
    ctx.verify_flags |= ssl.VERIFY_X509_PARTIAL_CHAIN
    ctx.load_verify_locations(cafile=str(trusted_client_cert))

    server = _QuietServer(("127.0.0.1", 0), _RecordingHandler)
    server.socket = ctx.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()


@contextmanager
def plain_http_server() -> Iterator[_QuietServer]:
    """
    Runs a plain (non-TLS) HTTP server that responds 200 to any GET.
    """
    server = _QuietServer(("127.0.0.1", 0), _RecordingHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
