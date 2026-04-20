import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from pylon_commons.models import Block
from pylon_commons.types import BlockHash, BlockNumber, Hotkey, RevealedCommitmentData

from tests.world import REVEALED_COMMITMENTS_NETUID


@pytest.mark.asyncio
async def test_v1_identity_get_own_revealed_commitments_returns_list(
    identity_test_client_factory, mock_bt_client_factory, snapshot_json
):
    async with mock_bt_client_factory("sn2") as mock_client:
        own_hotkey = mock_client.hotkey
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

        async with mock_client.mock_behavior(
            get_revealed_commitments=[lambda netuid, block, hotkey=None: revealed_by_hotkey.get(hotkey or own_hotkey)]
        ):
            async with identity_test_client_factory("sn2") as client:
                response = await client.get(
                    f"/api/v1/identity/sn2/subnet/{REVEALED_COMMITMENTS_NETUID}/block/latest/commitments/revealed/self"
                )

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_v1_identity_get_own_revealed_commitments_returns_404_when_missing(
    identity_test_client_factory, mock_bt_client_factory, snapshot_json
):
    async with mock_bt_client_factory("sn2") as mock_client:
        async with mock_client.mock_behavior(
            get_latest_block=[Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))],
            get_revealed_commitments=[None],
        ):
            async with identity_test_client_factory("sn2") as client:
                response = await client.get(
                    f"/api/v1/identity/sn2/subnet/{REVEALED_COMMITMENTS_NETUID}/block/latest/commitments/revealed/self"
                )

    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json() == snapshot_json
