import pytest
from litestar.status_codes import HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient
from pylon_commons.models import Block
from pylon_commons.types import BlockHash, BlockNumber

from tests.mock_bittensor_client import MockBittensorClient


@pytest.mark.asyncio
async def test_get_own_commitment_identity_not_found(
    test_client: AsyncTestClient, sn2_mock_bt_client: MockBittensorClient
):
    latest_block = Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))

    async with sn2_mock_bt_client.mock_behavior(
        get_latest_block=[latest_block],
        get_commitment=[None],
    ):
        response = await test_client.get("/api/v1/identity/sn2/subnet/2/block/latest/commitments/self")

    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json() == {
        "detail": "Commitment not found.",
        "status_code": HTTP_404_NOT_FOUND,
    }
