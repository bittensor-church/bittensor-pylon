import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from pylon_commons.models import Block
from pylon_commons.types import BlockHash, BlockNumber, Hotkey, RevealedCommitmentData

from tests.world import REVEALED_COMMITMENTS_NETUID


@pytest.mark.asyncio
async def test_unstable_open_access_get_revealed_commitments_by_hotkey_returns_list(
    open_access_test_client, mock_bt_client_factory, snapshot_json
):
    revealed_by_hotkey = {
        Hotkey("hotkey1"): [
            {
                "reveal_block_number": BlockNumber(703),
                "hotkey": Hotkey("hotkey1"),
                "commitment": RevealedCommitmentData("model-a"),
            },
            {
                "reveal_block_number": BlockNumber(704),
                "hotkey": Hotkey("hotkey1"),
                "commitment": RevealedCommitmentData("model-b"),
            },
        ],
        Hotkey("hotkey2"): [
            {
                "reveal_block_number": BlockNumber(705),
                "hotkey": Hotkey("hotkey2"),
                "commitment": RevealedCommitmentData("other-model"),
            },
        ],
    }

    def resolve_revealed_commitments(netuid, block, hotkey=None):
        if hotkey is None:
            return None
        return revealed_by_hotkey.get(hotkey)

    async with mock_bt_client_factory() as mock_client:
        async with mock_client.mock_behavior(get_revealed_commitments=[resolve_revealed_commitments]):
            response = await open_access_test_client.get(
                f"/api/_unstable/openaccess/subnet/{REVEALED_COMMITMENTS_NETUID}/block/latest/commitments/revealed/hotkey1"
            )

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_unstable_open_access_get_revealed_commitments_by_hotkey_returns_404_when_missing(
    open_access_test_client, mock_bt_client_factory, snapshot_json
):
    async with mock_bt_client_factory() as mock_client:
        async with mock_client.mock_behavior(
            get_latest_block=[Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))],
            get_revealed_commitments=[None],
        ):
            response = await open_access_test_client.get(
                f"/api/_unstable/openaccess/subnet/{REVEALED_COMMITMENTS_NETUID}/block/latest/commitments/revealed/hotkey1"
            )

    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json() == snapshot_json
