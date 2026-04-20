import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from pylon_commons.models import Block
from pylon_commons.types import BlockHash, BlockNumber

from tests.world import OWN_COMMITMENT_NETUID


@pytest.mark.asyncio
async def test_v1_identity_get_own_commitment_returns_v1_commitment_shape(identity_test_client_factory, snapshot_json):
    async with identity_test_client_factory("sn24") as client:
        response = await client.get(
            f"/api/v1/identity/sn24/subnet/{OWN_COMMITMENT_NETUID}/block/latest/commitments/self",
        )

        assert response.status_code == HTTP_200_OK
        assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_get_own_commitment_identity_not_found(
    identity_test_client_factory, mock_bt_client_factory, snapshot_json
):
    async with mock_bt_client_factory("sn2") as mock_client:
        latest_block = Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))

        async with mock_client.mock_behavior(
            get_latest_block=[latest_block],
            get_commitment=[None],
        ):
            async with identity_test_client_factory("sn2") as client:
                response = await client.get(
                    "/api/v1/identity/sn2/subnet/2/block/latest/commitments/self",
                )

        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_v1_identity_get_own_commitment_unknown_identity_returns_404(identity_test_client_factory, snapshot_json):
    async with identity_test_client_factory("sn1") as client:
        response = await client.get(
            "/api/v1/identity/unknown/subnet/1/block/latest/commitments/self",
        )

        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.json() == snapshot_json
