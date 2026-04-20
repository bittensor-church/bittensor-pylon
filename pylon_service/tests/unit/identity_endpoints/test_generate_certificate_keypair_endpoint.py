"""
Tests for the POST /identity/{identity_name}/subnet/{netuid}/certificates/self endpoint.
"""

import pytest
from litestar.status_codes import HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_502_BAD_GATEWAY
from pylon_commons.models import (
    CertificateAlgorithm,
    NeuronCertificateKeypair,
    PrivateKey,
    PublicKey,
)


@pytest.mark.asyncio
async def test_generate_certificate_keypair_identity_success(
    identity_test_client_factory, mock_bt_client_factory, snapshot_json
):
    """
    Test generating a certificate keypair successfully.
    """
    keypair = NeuronCertificateKeypair(
        algorithm=CertificateAlgorithm.ED25519,
        public_key=PublicKey("0xpublic123456789"),
        private_key=PrivateKey("0xprivate987654321"),
    )

    async with mock_bt_client_factory("sn1") as mock_client:
        async with mock_client.mock_behavior(
            generate_certificate_keypair=[keypair],
        ):
            async with identity_test_client_factory("sn1") as client:
                response = await client.post(
                    "/api/v1/identity/sn1/subnet/1/certificates/self",
                    json={"algorithm": 1},
                )

                assert response.status_code == HTTP_201_CREATED
                assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_generate_certificate_keypair_identity_default_algorithm(
    identity_test_client_factory, mock_bt_client_factory, snapshot_json
):
    """
    Test generating a certificate keypair with default algorithm.
    """
    keypair = NeuronCertificateKeypair(
        algorithm=CertificateAlgorithm.ED25519,
        public_key=PublicKey("0xpublic_default"),
        private_key=PrivateKey("0xprivate_default"),
    )

    async with mock_bt_client_factory("sn2") as mock_client:
        async with mock_client.mock_behavior(
            generate_certificate_keypair=[keypair],
        ):
            async with identity_test_client_factory("sn2") as client:
                response = await client.post(
                    "/api/v1/identity/sn2/subnet/2/certificates/self",
                    json={},
                )

                assert response.status_code == HTTP_201_CREATED
                assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_generate_certificate_keypair_identity_failure(
    identity_test_client_factory, mock_bt_client_factory, snapshot_json
):
    """
    Test generating a certificate keypair when generation fails.
    """
    async with mock_bt_client_factory("sn1") as mock_client:
        async with mock_client.mock_behavior(
            generate_certificate_keypair=[None],
        ):
            async with identity_test_client_factory("sn1") as client:
                response = await client.post(
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
    identity_test_client_factory, algorithm, snapshot_json
):
    """
    Test generating a certificate keypair with invalid algorithm.
    """
    async with identity_test_client_factory("sn1") as client:
        response = await client.post(
            "/api/v1/identity/sn1/subnet/1/certificates/self",
            json={"algorithm": algorithm},
        )

        assert response.status_code == HTTP_400_BAD_REQUEST, response.json()
        assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_v1_identity_generate_certificate_keypair_unknown_identity_returns_404(
    identity_test_client_factory, snapshot_json
):
    async with identity_test_client_factory("sn1") as client:
        response = await client.post(
            "/api/v1/identity/unknown/subnet/1/certificates/self",
            json={"algorithm": 1},
        )

        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.json() == snapshot_json
