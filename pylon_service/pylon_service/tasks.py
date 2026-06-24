import structlog
from litestar import Litestar
from pylon_commons.types import MechanismId

from pylon_service.api._unstable.tasks import ApplyWeights
from pylon_service.db.models import TaskStatus, WeightTask
from pylon_service.db.weight_task import get_running_tasks, update_weight_task_status
from pylon_service.identities import Identity, identities

logger = structlog.stdlib.get_logger(__name__)


async def reschedule_weight_tasks(app: Litestar) -> None:
    weight_tasks = await get_running_tasks()
    for identity_name in weight_tasks:
        identity = identities.get(identity_name)
        if identity is None:
            logger.warning("weight_tasks_cancelled_missing_identity", identity_name=identity_name)
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
                logger.error("weight_task_cancelled_identity_changed", identity_name=identity.identity_name)
                await update_weight_task_status(task.id, TaskStatus.CANCELLED)
            elif task.mechanism_id in rescheduled_mechanism_ids:
                await update_weight_task_status(task.id, TaskStatus.CANCELLED)
                logger.warning(
                    "duplicate_weight_task_cancelled",
                    identity_name=task.identity_name,
                    mechanism_id=task.mechanism_id,
                )
            else:
                await ApplyWeights.from_persisted_task(identity, contact_router, task).schedule()
                rescheduled_mechanism_ids.add(task.mechanism_id)
                logger.info(
                    "weight_task_rescheduled",
                    identity_name=task.identity_name,
                    mechanism_id=task.mechanism_id,
                )
