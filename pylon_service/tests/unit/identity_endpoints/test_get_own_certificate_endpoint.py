"""
Tests for the GET /identity/{identity_name}/subnet/{netuid}/block/latest/certificates/self endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from pylon_commons.models import Block, CertificateAlgorithm, NeuronCertificate
from pylon_commons.types import BlockHash, BlockNumber, PublicKey


@pytest.mark.asyncio
async def test_get_own_certificate_identity_success(
    identity_test_client_factory, mock_bt_client_factory, snapshot_json
):
    """
    Test getting own certificate successfully.
    """
    certificate = NeuronCertificate(
        algorithm=CertificateAlgorithm.ED25519,
        public_key=PublicKey("0xabcdef1234567890"),
    )
    latest_block = Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))

    async with mock_bt_client_factory("sn1") as mock_client:
        async with mock_client.mock_behavior(
            get_latest_block=[latest_block],
            get_certificate=[certificate],
        ):
            async with identity_test_client_factory("sn1") as client:
                response = await client.get(
                    "/api/v1/identity/sn1/subnet/1/block/latest/certificates/self",
                )

                assert response.status_code == HTTP_200_OK
                assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_get_own_certificate_identity_not_found(
    identity_test_client_factory, mock_bt_client_factory, snapshot_json
):
    """
    Test getting own certificate when it doesn't exist.
    """
    latest_block = Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))

    async with mock_bt_client_factory("sn2") as mock_client:
        async with mock_client.mock_behavior(
            get_latest_block=[latest_block],
            get_certificate=[None],
        ):
            async with identity_test_client_factory("sn2") as client:
                response = await client.get(
                    "/api/v1/identity/sn2/subnet/2/block/latest/certificates/self",
                )

                assert response.status_code == HTTP_404_NOT_FOUND
                assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_v1_identity_get_own_certificate_unknown_identity_returns_404(
    identity_test_client_factory, snapshot_json
):
    async with identity_test_client_factory("sn1") as client:
        response = await client.get(
            "/api/v1/identity/unknown/subnet/1/block/latest/certificates/self",
        )

        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.json() == snapshot_json
