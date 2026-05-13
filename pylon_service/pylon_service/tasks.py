import logging

from litestar import Litestar
from pylon_commons.types import MechanismId

from pylon_service.api._unstable.tasks import ApplyWeights
from pylon_service.db.models import TaskStatus, WeightTask
from pylon_service.db.weight_task import get_running_tasks, update_weight_task_status
from pylon_service.identities import Identity, identities

logger = logging.getLogger(__name__)


async def reschedule_weight_tasks(app: Litestar) -> None:
    weight_tasks = await get_running_tasks()
    for identity_name in weight_tasks:
        identity = identities.get(identity_name)
        if identity is None:
            logger.warning("Weight tasks cancelled due to missing identity %s", identity_name)
            for task in weight_tasks[identity_name]:
                await update_weight_task_status(task.id, TaskStatus.CANCELLED)
        else:
            await _reschedule_weight_tasks_for_identity(app, identity, weight_tasks[identity_name])


async def _reschedule_weight_tasks_for_identity(app: Litestar, identity: Identity, tasks: list[WeightTask]) -> None:
    sorted_tasks = sorted(tasks, key=lambda task: task.created_at, reverse=True)
    bt_contact_pool = app.state.bittensor_contact_pool
    async with bt_contact_pool.acquire(wallet=identity.wallet) as contact_router:
        rescheduled_mechanism_ids: set[MechanismId] = set()
        for task in sorted_tasks:
            if task.netuid != identity.netuid or task.hotkey != identity.wallet.hotkey.ss58_address:
                logger.error(
                    "Weight set task cancelled due to identity %s configuration change", identity.identity_name
                )
                await update_weight_task_status(task.id, TaskStatus.CANCELLED)
            elif task.mechanism_id in rescheduled_mechanism_ids:
                await update_weight_task_status(task.id, TaskStatus.CANCELLED)
                logger.warning(
                    "Duplicate weight set task cancelled (identity=%s, mechanism_id=%s)",
                    task.identity_name,
                    task.mechanism_id,
                )
            else:
                await ApplyWeights(identity, contact_router, rescheduled_task=task).schedule()
                rescheduled_mechanism_ids.add(task.mechanism_id)
                logger.info(
                    "Weight set task rescheduled (identity=%s, mechanism_id=%s)", task.identity_name, task.mechanism_id
                )
