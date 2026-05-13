"""
Unit tests for the GET /identity/{identity_name}/subnet/{netuid}/mechanism/{mechanism_id}/block/{block_number}/weights/status endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK
from pylon_commons.types import (
    BlockNumber,
    Hotkey,
    IdentityName,
    MechanismId,
    NetUid,
    Weight,
)

from pylon_service.db.models import TaskStatus, WeightTask
from tests.integration.localchain.dev_accounts import DevAccount


def _create_weight_task(
    *,
    identity_name: IdentityName = IdentityName("sn1"),
    netuid: NetUid = NetUid(1),
    hotkey: Hotkey = Hotkey(DevAccount.ALICE.hotkey_ss58),
    mechanism_id: MechanismId = MechanismId(1),
    status: TaskStatus = TaskStatus.RUNNING,
    start_block_number: BlockNumber | None = BlockNumber(1000),
):
    return WeightTask(
        identity_name=identity_name,
        netuid=netuid,
        hotkey=hotkey,
        mechanism_id=mechanism_id,
        weights={Hotkey("hotkey1"): Weight(0.5)},
        status=status,
        start_block_number=start_block_number,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "task_status, start_block_number",
    [
        pytest.param(TaskStatus.RUNNING, BlockNumber(1000), id="running_task"),
        pytest.param(TaskStatus.RUNNING, None, id="running_task_with_no_start_block_number"),
        pytest.param(TaskStatus.SUCCEEDED, BlockNumber(1000), id="succeeded_task"),
    ],
)
async def test_get_mechanism_weight_status_finds_matching_task(
    identity_test_client_factory,
    mock_bt_client_factory,
    seed_running_weight_task_before_reschedule,
    task_status: TaskStatus,
    start_block_number: BlockNumber | None,
):
    seed_running_weight_task_before_reschedule.append(
        _create_weight_task(status=task_status, start_block_number=start_block_number)
    )
    async with mock_bt_client_factory() as mock_client:
        async with mock_client.mock_behavior():
            async with identity_test_client_factory("sn1") as client:
                response = await client.get(
                    "/api/_unstable/identity/sn1/subnet/1/mechanism/1/block/1000/weights/status"
                )

                assert response.status_code == HTTP_200_OK
                assert response.json() == {"weights_submitted": True}


@pytest.mark.asyncio
async def test_get_mechanism_weight_status_ignores_not_matching_tasks(
    identity_test_client_factory,
    mock_bt_client_factory,
    seed_running_weight_task_before_reschedule,
):
    seed_running_weight_task_before_reschedule.extend(
        [
            _create_weight_task(identity_name=IdentityName("sn2")),
            _create_weight_task(netuid=NetUid(2)),
            _create_weight_task(hotkey=Hotkey("wrong_hotkey")),
            _create_weight_task(mechanism_id=MechanismId(2)),
            _create_weight_task(start_block_number=BlockNumber(100)),
            _create_weight_task(status=TaskStatus.FAILED),
            _create_weight_task(status=TaskStatus.CANCELLED),
            _create_weight_task(status=TaskStatus.EXPIRED),
        ]
    )
    async with mock_bt_client_factory() as mock_client:
        async with mock_client.mock_behavior():
            async with identity_test_client_factory("sn1") as client:
                response = await client.get(
                    "/api/_unstable/identity/sn1/subnet/1/mechanism/1/block/1000/weights/status"
                )

                assert response.status_code == HTTP_200_OK
                assert response.json() == {"weights_submitted": False}
