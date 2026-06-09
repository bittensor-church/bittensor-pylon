"""
Tests for the GET /subnet/{netuid}/block/latest/certificates/{hotkey} endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from pylon_commons.models import Block, CertificateAlgorithm, NeuronCertificate
from pylon_commons.types import BlockHash, BlockNumber, PublicKey


@pytest.mark.asyncio
async def test_get_certificate_open_access_success(open_access_test_client, mock_bt_client_factory, snapshot_json):
    """
    Test getting a specific certificate successfully.
    """
    hotkey = "hotkey1"
    certificate = NeuronCertificate(
        algorithm=CertificateAlgorithm.ED25519,
        public_key=PublicKey("0x1234567890abcdef"),
    )
    latest_block = Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))

    async with mock_bt_client_factory() as mock_client:
        async with mock_client.mock_behavior(
            get_latest_block=[latest_block],
            get_certificate=[certificate],
        ):
            response = await open_access_test_client.get(
                f"/api/_unstable/openaccess/subnet/1/block/latest/certificates/{hotkey}"
            )

            assert response.status_code == HTTP_200_OK
            assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_get_certificate_open_access_not_found(open_access_test_client, mock_bt_client_factory, snapshot_json):
    """
    Test getting a certificate that doesn't exist.
    """
    hotkey = "hotkey1"
    latest_block = Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))

    async with mock_bt_client_factory() as mock_client:
        async with mock_client.mock_behavior(
            get_latest_block=[latest_block],
            get_certificate=[None],
        ):
            response = await open_access_test_client.get(
                f"/api/_unstable/openaccess/subnet/1/block/latest/certificates/{hotkey}"
            )

            assert response.status_code == HTTP_404_NOT_FOUND
            assert response.json() == snapshot_json
