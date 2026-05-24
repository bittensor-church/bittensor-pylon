from ipaddress import ip_address

import httpx
import pytest
from tenacity import wait_none

from pylon_client._internal.pylon_commons.types import Port
from pylon_client._internal.pylon_commons.v1.endpoints import Endpoint as V1Endpoint
from pylon_client.artanis import (
    ASYNC_DEFAULT_RETRIES,
    AsyncConfig,
    AsyncPylonClient,
    IdentityName,
    NetUid,
    PylonAuthToken,
)
from tests.factories import NeuronFactory
from tests.mtls_helpers import generate_ed25519_cert, mtls_server, plain_http_server
from tests.neurons_file_helpers import write_neurons_file


@pytest.mark.asyncio
async def test_no_cert_yields_plain_client(test_url, neuron_factory: NeuronFactory):
    """
    Test that get_neuron_client yields a plain httpx client when cert/key are not configured.
    """
    client = AsyncPylonClient(
        AsyncConfig(
            address=test_url,
            open_access_token=PylonAuthToken("tok"),
            retry=ASYNC_DEFAULT_RETRIES.copy(wait=wait_none()),
        )
    )
    neuron = neuron_factory.build()
    async with client:
        async with client.get_neuron_client(neuron) as http_client:
            assert isinstance(http_client, httpx.AsyncClient)


@pytest.mark.asyncio
async def test_mtls_connection_presents_client_cert(tmp_path, test_url, neuron_factory: NeuronFactory, service_mock):
    """
    Test that get_neuron_client performs a real mTLS connection: it verifies the miner's pinned cert
    and presents its own client certificate (which the server records).
    """
    server_cert = tmp_path / "server.crt"
    server_key = tmp_path / "server.key"
    client_cert = tmp_path / "client.crt"
    client_key = tmp_path / "client.key"
    server_pubkey_hex = generate_ed25519_cert("miner", server_cert, server_key)
    generate_ed25519_cert("validator", client_cert, client_key)

    with mtls_server(server_cert, server_key, trusted_client_cert=client_cert) as server:
        port = server.server_address[1]
        neuron = neuron_factory.build()
        neuron.axon_info.ip = ip_address("127.0.0.1")
        neuron.axon_info.port = Port(port)

        service_mock.get(V1Endpoint.IDENTITIES.absolute_url()).mock(
            return_value=httpx.Response(200, json={"identities": {"sn1": 1}})
        )
        cert_url = V1Endpoint.CERTIFICATES_HOTKEY.absolute_url(
            netuid_=NetUid(1), identity_name_=IdentityName("sn1"), hotkey=neuron.hotkey
        )
        service_mock.get(cert_url).mock(
            return_value=httpx.Response(200, json={"algorithm": 1, "public_key": server_pubkey_hex})
        )
        # Let the real miner connection bypass respx and hit the test server.
        service_mock.route(host="127.0.0.1").pass_through()

        client = AsyncPylonClient(
            AsyncConfig(
                address=test_url,
                identity_name=IdentityName("sn1"),
                identity_token=PylonAuthToken("sn1_token"),
                mtls_cert_path=str(client_cert),
                mtls_key_path=str(client_key),
                retry=ASYNC_DEFAULT_RETRIES.copy(wait=wait_none()),
            )
        )
        async with client:
            async with client.get_neuron_client(neuron) as http_client:
                response = await http_client.get("/")

        assert response.status_code == 200
        assert server.client_cert_der is not None


@pytest.mark.asyncio
async def test_plain_http_connection(test_url, neuron_factory: NeuronFactory):
    """
    Test that get_neuron_client performs a real plain-HTTP connection when no mTLS cert is configured,
    presenting no client certificate.
    """
    with plain_http_server() as server:
        port = server.server_address[1]
        neuron = neuron_factory.build()
        neuron.axon_info.ip = ip_address("127.0.0.1")
        neuron.axon_info.port = Port(port)

        client = AsyncPylonClient(
            AsyncConfig(
                address=test_url,
                open_access_token=PylonAuthToken("tok"),
                retry=ASYNC_DEFAULT_RETRIES.copy(wait=wait_none()),
            )
        )
        async with client:
            async with client.get_neuron_client(neuron) as http_client:
                response = await http_client.get("/")

        assert response.status_code == 200
        assert server.client_cert_der is None


@pytest.mark.asyncio
async def test_neurons_file_yields_plain_client(tmp_path, test_url, neuron_factory: NeuronFactory):
    """
    Test that get_neuron_client yields a plain httpx client when neurons_file is set,
    even when mtls_cert_path and mtls_key_path are also configured.
    """
    neurons_file = tmp_path / "neurons.yaml"
    write_neurons_file(neurons_file, {})
    cert_file = tmp_path / "cert.pem"
    key_file = tmp_path / "key.pem"
    cert_file.write_text("cert")
    key_file.write_text("key")
    client = AsyncPylonClient(
        AsyncConfig(
            address=test_url,
            open_access_token=PylonAuthToken("tok"),
            neurons_file=str(neurons_file),
            mtls_cert_path=str(cert_file),
            mtls_key_path=str(key_file),
            retry=ASYNC_DEFAULT_RETRIES.copy(wait=wait_none()),
        )
    )
    neuron = neuron_factory.build()
    async with client:
        async with client.get_neuron_client(neuron) as http_client:
            assert isinstance(http_client, httpx.AsyncClient)
