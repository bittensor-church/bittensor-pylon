from collections import defaultdict

from pylon_commons.types import BlockNumber, Hotkey, IdentityName, MechanismId, NetUid, Weight
from sqlalchemy import or_, select, update

from pylon_service.api.epoch import Epoch
from pylon_service.db.database import session_factory
from pylon_service.db.models import TaskStatus, WeightTask
from pylon_service.identities import Identity


async def create_weight_task_and_cancel_duplicate_tasks(
    identity_name: IdentityName,
    weights: dict[Hotkey, Weight],
    netuid: NetUid,
    mechanism_id: MechanismId,
    hotkey: Hotkey,
) -> int:
    async with session_factory() as session:
        async with session.begin():
            await session.execute(
                update(WeightTask)
                .where(
                    WeightTask.identity_name == identity_name,
                    WeightTask.mechanism_id == mechanism_id,
                    WeightTask.status == TaskStatus.RUNNING,
                )
                .values(status=TaskStatus.CANCELLED)
            )
            task = WeightTask(
                identity_name=identity_name,
                weights=weights,
                netuid=netuid,
                mechanism_id=mechanism_id,
                hotkey=hotkey,
                start_block_number=None,
            )
            session.add(task)
        await session.refresh(task)
        return task.id


async def get_weight_task_status(task_id: int) -> TaskStatus | None:
    async with session_factory() as session:
        task = await session.get(WeightTask, task_id)
        return task.status if task else None


async def update_weight_task_status(task_id: int, status: TaskStatus, *, only_if_running: bool = False) -> None:
    async with session_factory() as session:
        async with session.begin():
            task = await session.get(WeightTask, task_id)
            if task is None:
                raise ValueError(f"WeightTask with id={task_id} does not exist")
            if only_if_running and task.status != TaskStatus.RUNNING:
                return
            task.status = status


async def set_weight_task_start_block_number(task_id: int, start_block_number: BlockNumber) -> None:
    async with session_factory() as session:
        async with session.begin():
            task = await session.get(WeightTask, task_id)
            if task is None:
                raise ValueError(f"WeightTask with id={task_id} does not exist")

            task.start_block_number = start_block_number


async def get_running_tasks() -> defaultdict[IdentityName, list[WeightTask]]:
    async with session_factory() as session:
        statement = select(WeightTask).where(WeightTask.status == TaskStatus.RUNNING)
        tasks = await session.scalars(statement)

        tasks_by_identity_name = defaultdict(list)

        for task in tasks:
            tasks_by_identity_name[task.identity_name].append(task)

        return tasks_by_identity_name


async def weight_task_submitted(identity: Identity, mechanism_id: MechanismId, epoch: Epoch) -> bool:
    async with session_factory() as session:
        statement = select(
            select(WeightTask.id)
            .where(
                WeightTask.identity_name == identity.identity_name,
                WeightTask.mechanism_id == mechanism_id,
                WeightTask.status.in_([TaskStatus.RUNNING, TaskStatus.SUCCEEDED]),
                or_(
                    WeightTask.start_block_number.is_(None),
                    WeightTask.start_block_number.between(epoch.start, epoch.end),
                ),
            )
            .exists()
        )

        return bool(await session.scalar(statement))
