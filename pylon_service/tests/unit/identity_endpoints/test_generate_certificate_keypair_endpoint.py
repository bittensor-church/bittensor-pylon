"""
Tests for the POST /identity/{identity_name}/subnet/{netuid}/certificates/self endpoint.
"""

import pytest
from litestar.status_codes import HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_502_BAD_GATEWAY
from litestar.testing import AsyncTestClient
from pylon_commons.models import (
    CertificateAlgorithm,
    NeuronCertificateKeypair,
    PrivateKey,
    PublicKey,
)

from tests.mock_bittensor_client import MockBittensorClient


@pytest.mark.asyncio
async def test_generate_certificate_keypair_identity_success(
    test_client: AsyncTestClient, sn1_mock_bt_client: MockBittensorClient, snapshot_json
):
    """
    Test generating a certificate keypair successfully.
    """
    keypair = NeuronCertificateKeypair(
        algorithm=CertificateAlgorithm.ED25519,
        public_key=PublicKey("0xpublic123456789"),
        private_key=PrivateKey("0xprivate987654321"),
    )

    async with sn1_mock_bt_client.mock_behavior(
        generate_certificate_keypair=[keypair],
    ):
        response = await test_client.post(
            "/api/v1/identity/sn1/subnet/1/certificates/self",
            json={"algorithm": 1},
        )

        assert response.status_code == HTTP_201_CREATED
        assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_generate_certificate_keypair_identity_default_algorithm(
    test_client: AsyncTestClient, sn2_mock_bt_client: MockBittensorClient, snapshot_json
):
    """
    Test generating a certificate keypair with default algorithm.
    """
    keypair = NeuronCertificateKeypair(
        algorithm=CertificateAlgorithm.ED25519,
        public_key=PublicKey("0xpublic_default"),
        private_key=PrivateKey("0xprivate_default"),
    )

    async with sn2_mock_bt_client.mock_behavior(
        generate_certificate_keypair=[keypair],
    ):
        response = await test_client.post(
            "/api/v1/identity/sn2/subnet/2/certificates/self",
            json={},
        )

        assert response.status_code == HTTP_201_CREATED
        assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_generate_certificate_keypair_identity_failure(
    test_client: AsyncTestClient, sn1_mock_bt_client: MockBittensorClient, snapshot_json
):
    """
    Test generating a certificate keypair when generation fails.
    """
    async with sn1_mock_bt_client.mock_behavior(
        generate_certificate_keypair=[None],
    ):
        response = await test_client.post(
            "/api/v1/identity/sn1/subnet/1/certificates/self",
            json={"algorithm": 1},
        )

        assert response.status_code == HTTP_502_BAD_GATEWAY
        assert response.json() == snapshot_json


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "algorithm",
    [
        pytest.param(0, id="algorithm_zero"),
        pytest.param(2, id="algorithm_two"),
        pytest.param("invalid", id="invalid_type"),
    ],
)
async def test_generate_certificate_keypair_identity_invalid_algorithm(
    test_client: AsyncTestClient, algorithm, snapshot_json
):
    """
    Test generating a certificate keypair with invalid algorithm.
    """
    response = await test_client.post(
        "/api/v1/identity/sn1/subnet/1/certificates/self",
        json={"algorithm": algorithm},
    )

    assert response.status_code == HTTP_400_BAD_REQUEST, response.json()
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_v1_identity_generate_certificate_keypair_unknown_identity_returns_404(test_client, snapshot_json):
    response = await test_client.post(
        "/api/v1/identity/unknown/subnet/1/certificates/self",
        json={"algorithm": 1},
    )

    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json() == snapshot_json
