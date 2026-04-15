import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient
from pylon_commons.models import Block
from pylon_commons.types import BlockHash, BlockNumber, Hotkey, RevealedCommitmentData

from pylon_service.bittensor.contact import MockBittensorContact
from tests.world import REVEALED_COMMITMENTS_NETUID


@pytest.mark.asyncio
async def test_unstable_identity_get_own_revealed_commitments_returns_list(
    test_client: AsyncTestClient, sn2_mock_bt_client: MockBittensorContact, snapshot_json
):
    own_hotkey = sn2_mock_bt_client.hotkey
    revealed_by_hotkey = {
        own_hotkey: [
            {
                "reveal_block_number": BlockNumber(705),
                "hotkey": own_hotkey,
                "commitment": RevealedCommitmentData("self-model-a"),
            },
            {
                "reveal_block_number": BlockNumber(706),
                "hotkey": own_hotkey,
                "commitment": RevealedCommitmentData("self-model-b"),
            },
        ],
        Hotkey("hotkey1"): [
            {
                "reveal_block_number": BlockNumber(703),
                "hotkey": Hotkey("hotkey1"),
                "commitment": RevealedCommitmentData("foreign-model"),
            },
        ],
    }

    async with sn2_mock_bt_client.mock_behavior(
        get_revealed_commitments=[lambda netuid, block, hotkey=None: revealed_by_hotkey.get(hotkey or own_hotkey)]
    ):
        response = await test_client.get(
            f"/api/_unstable/identity/sn2/subnet/{REVEALED_COMMITMENTS_NETUID}/block/latest/commitments/revealed/self"
        )

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_unstable_identity_get_own_revealed_commitments_returns_404_when_missing(
    test_client: AsyncTestClient, sn2_mock_bt_client: MockBittensorContact, snapshot_json
):
    async with sn2_mock_bt_client.mock_behavior(
        get_latest_block=[Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))],
        get_revealed_commitments=[None],
    ):
        response = await test_client.get(
            f"/api/_unstable/identity/sn2/subnet/{REVEALED_COMMITMENTS_NETUID}/block/latest/commitments/revealed/self"
        )

    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json() == snapshot_json
