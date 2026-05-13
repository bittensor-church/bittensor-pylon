from contextlib import asynccontextmanager

import pytest
from litestar.testing import AsyncTestClient
from pylon_commons.types import BlockNumber, Hotkey, IdentityName, MechanismId, NetUid, NeuronUid, Weight
from sqlalchemy import select

from pylon_service.db.database import session_factory
from pylon_service.db.models import TaskStatus, WeightTask
from tests.helpers import db_row_model_dump, wait_for_background_tasks
from tests.integration.localchain.dev_accounts import DevAccount


def _create_sn1_weight_task(mechanism_id: MechanismId, weights: dict[Hotkey, Weight], status: TaskStatus):
    return WeightTask(
        identity_name=IdentityName("sn1"),
        netuid=NetUid(1),
        hotkey=DevAccount.ALICE.hotkey_ss58,
        mechanism_id=mechanism_id,
        weights=weights,
        status=status,
        start_block_number=BlockNumber(1000),
    )


def _create_sn2_weight_task(mechanism_id: MechanismId, weights: dict[Hotkey, Weight], status: TaskStatus):
    return WeightTask(
        identity_name=IdentityName("sn2"),
        netuid=NetUid(2),
        hotkey=DevAccount.BOB.hotkey_ss58,
        mechanism_id=mechanism_id,
        weights=weights,
        status=status,
        start_block_number=BlockNumber(1000),
    )


@pytest.fixture
def test_client_factory(test_app):
    @asynccontextmanager
    async def _factory():
        async with AsyncTestClient(app=test_app) as client:
            yield client

    return _factory


@pytest.mark.asyncio
async def test_service_reschedules_single_weight_tasks(
    seed_running_weight_task_before_reschedule, test_client_factory, mock_bt_client_factory
):
    weight_task = _create_sn1_weight_task(MechanismId(0), {Hotkey("hotkey1"): Weight(0.5)}, TaskStatus.RUNNING)
    seed_running_weight_task_before_reschedule.append(weight_task)

    async with mock_bt_client_factory("sn1") as mock_client:
        async with mock_client.mock_behavior():
            async with test_client_factory():
                await wait_for_background_tasks()

                assert mock_client.calls["set_weights"] == [
                    (
                        NetUid(1),
                        MechanismId(0),
                        {
                            NeuronUid(1): 0.5,
                        },
                    ),
                ]

                async with session_factory() as session:
                    result = await session.scalars(select(WeightTask))
                    tasks = list(result)

                assert len(tasks) == 1

                task = tasks[0]
                assert db_row_model_dump(task) == {
                    **db_row_model_dump(weight_task),
                    "status": TaskStatus.SUCCEEDED,
                }


@pytest.mark.asyncio
async def test_service_does_not_reschedule_tasks_not_running(
    seed_running_weight_task_before_reschedule, test_client_factory, mock_bt_client_factory
):
    tasks = [
        _create_sn1_weight_task(MechanismId(0), {Hotkey("hotkey1"): Weight(0.5)}, TaskStatus.SUCCEEDED),
        _create_sn1_weight_task(MechanismId(1), {Hotkey("hotkey2"): Weight(0.5)}, TaskStatus.FAILED),
        _create_sn1_weight_task(MechanismId(2), {Hotkey("hotkey3"): Weight(0.5)}, TaskStatus.CANCELLED),
        _create_sn1_weight_task(MechanismId(3), {Hotkey("hotkey4"): Weight(0.5)}, TaskStatus.EXPIRED),
    ]
    for task in tasks:
        seed_running_weight_task_before_reschedule.append(task)

    async with mock_bt_client_factory("sn1") as mock_client:
        async with mock_client.mock_behavior():
            async with test_client_factory():
                await wait_for_background_tasks()

                assert mock_client.calls["set_weights"] == []

                async with session_factory() as session:
                    result = await session.scalars(select(WeightTask).order_by(WeightTask.id))
                    db_tasks = list(result)

                assert len(db_tasks) == 4
                for i, task in enumerate(tasks):
                    assert db_row_model_dump(db_tasks[i]) == db_row_model_dump(task)


@pytest.mark.asyncio
async def test_service_deduplicates_tasks_while_rescheduling(
    seed_running_weight_task_before_reschedule, test_client_factory, mock_bt_client_factory
):
    task1 = _create_sn1_weight_task(MechanismId(0), {Hotkey("hotkey1"): Weight(0.5)}, TaskStatus.RUNNING)
    task2 = _create_sn1_weight_task(MechanismId(0), {Hotkey("hotkey1"): Weight(0.7)}, TaskStatus.RUNNING)

    seed_running_weight_task_before_reschedule.append(task1)
    seed_running_weight_task_before_reschedule.append(task2)

    async with mock_bt_client_factory("sn1") as mock_client:
        async with mock_client.mock_behavior():
            async with test_client_factory():
                await wait_for_background_tasks()

                # Only task2 should be executed
                assert mock_client.calls["set_weights"] == [
                    (
                        NetUid(1),
                        MechanismId(0),
                        {
                            NeuronUid(1): 0.7,
                        },
                    ),
                ]

                async with session_factory() as session:
                    result = await session.scalars(select(WeightTask).order_by(WeightTask.created_at))
                    db_tasks = list(result)

                assert len(db_tasks) == 2
                assert db_tasks[0].id == task1.id
                assert db_tasks[0].status == TaskStatus.CANCELLED
                assert db_tasks[1].id == task2.id
                assert db_tasks[1].status == TaskStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_service_reschedules_multiple_weight_tasks(
    seed_running_weight_task_before_reschedule, test_client_factory, mock_bt_client_factory
):
    tasks = [
        _create_sn1_weight_task(MechanismId(0), {Hotkey("hotkey1"): Weight(0.5)}, TaskStatus.RUNNING),
        _create_sn1_weight_task(MechanismId(1), {Hotkey("hotkey2"): Weight(0.5)}, TaskStatus.RUNNING),
        _create_sn2_weight_task(MechanismId(0), {Hotkey("hotkey3"): Weight(0.5)}, TaskStatus.RUNNING),
    ]
    for task in tasks:
        seed_running_weight_task_before_reschedule.append(task)

    async with mock_bt_client_factory("sn1") as mock_client_sn1, mock_bt_client_factory("sn2") as mock_client_sn2:
        async with mock_client_sn1.mock_behavior(), mock_client_sn2.mock_behavior():
            async with test_client_factory():
                await wait_for_background_tasks()

                assert len(mock_client_sn1.calls["set_weights"]) == 2
                assert len(mock_client_sn2.calls["set_weights"]) == 1

                async with session_factory() as session:
                    result = await session.scalars(select(WeightTask).order_by(WeightTask.id))
                    db_tasks = list(result)

                assert len(db_tasks) == 3
                for task in db_tasks:
                    assert task.status == TaskStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_service_cancels_unknown_identity_task_while_rescheduling(
    seed_running_weight_task_before_reschedule, test_client_factory, mock_bt_client_factory
):
    weight_task = WeightTask(
        identity_name=IdentityName("unknown"),
        netuid=NetUid(1),
        hotkey=Hotkey("hotkey1"),
        mechanism_id=MechanismId(0),
        weights={Hotkey("hotkey1"): Weight(0.5)},
        status=TaskStatus.RUNNING,
        start_block_number=BlockNumber(1000),
    )
    seed_running_weight_task_before_reschedule.append(weight_task)

    async with test_client_factory():
        await wait_for_background_tasks()

        async with session_factory() as session:
            result = await session.scalars(select(WeightTask))
            tasks = list(result)

        assert len(tasks) == 1
        assert tasks[0].status == TaskStatus.CANCELLED


@pytest.mark.asyncio
async def test_service_cancel_task_with_mismatched_netuid_while_rescheduling(
    seed_running_weight_task_before_reschedule, test_client_factory, mock_bt_client_factory
):
    weight_task = _create_sn1_weight_task(MechanismId(0), {Hotkey("hotkey1"): Weight(0.5)}, TaskStatus.RUNNING)
    weight_task.netuid = NetUid(99)
    seed_running_weight_task_before_reschedule.append(weight_task)

    async with mock_bt_client_factory("sn1") as mock_client:
        async with mock_client.mock_behavior():
            async with test_client_factory():
                await wait_for_background_tasks()

                assert mock_client.calls["set_weights"] == []

                async with session_factory() as session:
                    result = await session.scalars(select(WeightTask))
                    tasks = list(result)

                assert len(tasks) == 1
                assert tasks[0].status == TaskStatus.CANCELLED


@pytest.mark.asyncio
async def test_service_cancel_task_with_mismatched_hotkey_while_rescheduling(
    seed_running_weight_task_before_reschedule, test_client_factory, mock_bt_client_factory
):
    weight_task = _create_sn1_weight_task(MechanismId(0), {Hotkey("hotkey1"): Weight(0.5)}, TaskStatus.RUNNING)
    weight_task.hotkey = Hotkey("wrong_hotkey")
    seed_running_weight_task_before_reschedule.append(weight_task)

    async with mock_bt_client_factory("sn1") as mock_client:
        async with mock_client.mock_behavior():
            async with test_client_factory():
                await wait_for_background_tasks()

                assert mock_client.calls["set_weights"] == []

                async with session_factory() as session:
                    result = await session.scalars(select(WeightTask))
                    tasks = list(result)

                assert len(tasks) == 1
                assert tasks[0].status == TaskStatus.CANCELLED
