import pytest
from litestar.status_codes import HTTP_200_OK
from pylon_commons.models import Block, Commitment, SubnetCommitments, SubnetState
from pylon_commons.types import BlockHash, BlockNumber, Coldkey, Hotkey, NetUid

from tests.mock_bittensor_client import MockBittensorClient


def _build_subnet_state(registered_hotkeys: list[str], netuid: int = 1) -> SubnetState:
    count = len(registered_hotkeys)
    return SubnetState(
        netuid=NetUid(netuid),
        hotkeys=[Hotkey(hotkey) for hotkey in registered_hotkeys],
        coldkeys=[Coldkey(f"coldkey-{i}") for i in range(count)],
        active=[True] * count,
        validator_permit=[True] * count,
        pruning_score=[0] * count,
        last_update=[0] * count,
        emission=[0] * count,
        dividends=[0] * count,
        incentives=[0] * count,
        consensus=[0] * count,
        trust=[0] * count,
        rank=[0] * count,
        block_at_registration=[BlockNumber(1)] * count,
        alpha_stake=[0] * count,
        tao_stake=[0] * count,
        total_stake=[0] * count,
        emission_history=[[0] for _ in range(count)],
    )


def _build_commitment(block_number: int, hotkey: str, commitment_hex: str) -> Commitment:
    return Commitment(
        commitment_block_number=BlockNumber(block_number),
        hotkey=Hotkey(hotkey),
        commitment=commitment_hex,
    )


@pytest.mark.asyncio
async def test_v1_identity_get_commitments_returns_registered_commitments_as_hex_map(
    test_client, sn1_mock_bt_client: MockBittensorClient, snapshot_json
):
    block = Block(number=BlockNumber(700), hash=BlockHash("0xblock700"))
    commitments = SubnetCommitments(
        block=block,
        commitments={
            Hotkey("hotkey1"): _build_commitment(699, "hotkey1", "0xaaaa"),
            Hotkey("hotkey2"): _build_commitment(699, "hotkey2", "0xbbbb"),
        },
    )

    async with sn1_mock_bt_client.mock_behavior(
        get_latest_block=[block],
        get_commitments=[commitments],
        get_subnet_state=[_build_subnet_state(["hotkey1", "hotkey2"])],
    ):
        response = await test_client.get("/api/v1/identity/sn1/subnet/1/block/latest/commitments")

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_v1_identity_get_commitments_filters_unregistered_commitments_and_keeps_valid_items(
    test_client, sn1_mock_bt_client: MockBittensorClient, snapshot_json
):
    block = Block(number=BlockNumber(701), hash=BlockHash("0xblock701"))
    commitments = SubnetCommitments(
        block=block,
        commitments={
            Hotkey("hotkey1"): _build_commitment(700, "hotkey1", "0xaaaa"),
            Hotkey("foreign-hotkey"): _build_commitment(700, "foreign-hotkey", "0xffff"),
        },
    )

    async with sn1_mock_bt_client.mock_behavior(
        get_latest_block=[block],
        get_commitments=[commitments],
        get_subnet_state=[_build_subnet_state(["hotkey1"])],
    ):
        response = await test_client.get("/api/v1/identity/sn1/subnet/1/block/latest/commitments")

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_v1_identity_get_commitments_returns_empty_map_when_none_exist(
    test_client, sn1_mock_bt_client: MockBittensorClient, snapshot_json
):
    block = Block(number=BlockNumber(702), hash=BlockHash("0xblock702"))
    commitments = SubnetCommitments(block=block, commitments={})

    async with sn1_mock_bt_client.mock_behavior(
        get_latest_block=[block],
        get_commitments=[commitments],
        get_subnet_state=[_build_subnet_state([])],
    ):
        response = await test_client.get("/api/v1/identity/sn1/subnet/1/block/latest/commitments")

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json
