import httpx
import pytest
from tenacity import wait_none

from pylon_client.artanis import ASYNC_DEFAULT_RETRIES, AsyncConfig, AsyncPylonClient, PylonAuthToken
from tests.factories import NeuronFactory


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
async def test_neurons_file_yields_plain_client(tmp_path, test_url, neuron_factory: NeuronFactory):
    """
    Test that get_neuron_client yields a plain httpx client when neurons_file is set,
    even when mtls_cert_path and mtls_key_path are also configured.
    """
    neurons_file = tmp_path / "neurons.json"
    neurons_file.write_text("[]")
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
