"""
Tests for the GET /identity/{identity_name}/subnet/{netuid}/block/latest/certificates endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK
from pylon_commons.models import Block, CertificateAlgorithm, NeuronCertificate
from pylon_commons.types import BlockHash, BlockNumber, PublicKey


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "certificates_input",
    [
        pytest.param(
            {
                "hotkey1": NeuronCertificate(
                    algorithm=CertificateAlgorithm.ED25519,
                    public_key=PublicKey("0x1234567890abcdef"),
                ),
                "hothey2": NeuronCertificate(
                    algorithm=CertificateAlgorithm.ED25519,
                    public_key=PublicKey("0xfedcba0987654321"),
                ),
            },
            id="multiple_certificates",
        ),
        pytest.param(
            {},
            id="empty_certificates",
        ),
    ],
)
async def test_get_certificates_identity(
    identity_test_client_factory,
    mock_bt_client_factory,
    certificates_input: dict,
    snapshot_json,
):
    """
    Test getting certificates from the subnet.
    """
    latest_block = Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))
    async with mock_bt_client_factory("sn1") as mock_client:
        async with mock_client.mock_behavior(
            get_latest_block=[latest_block],
            get_certificates=[certificates_input],
        ):
            async with identity_test_client_factory("sn1") as client:
                response = await client.get(
                    "/api/_unstable/identity/sn1/subnet/1/block/latest/certificates",
                )

            assert response.status_code == HTTP_200_OK
            assert response.json() == snapshot_json
