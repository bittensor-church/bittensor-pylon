import pytest
import time_machine
from litestar.stores.base import Store
from pylon_commons.models import BittensorModel
from pylon_commons.types import NetUid, Timestamp
from tenacity import AsyncRetrying, stop_after_attempt

from pylon_service.bittensor.contact import BittensorPort
from pylon_service.bittensor.contact_router import BittensorContactRouter
from pylon_service.bittensor.mock_contact import Behave
from pylon_service.bittensor.pool import BittensorContactPool
from pylon_service.bittensor.recent import AbstractContext, RecentObjectUpdateTaskExecutor, SubnetContext
from pylon_service.bittensor.recent.adapter import CacheKey, _CacheEntry
from pylon_service.bittensor.recent.tasks import UpdateRecentObject


class AnObjectModel(BittensorModel):
    field_1: str
    field_2: int


class Task(UpdateRecentObject[AnObjectModel, SubnetContext]):
    def __init__(self, store: Store, pool: BittensorContactPool) -> None:
        super().__init__(store, pool)
        self.behave = Behave()

    @property
    def _model(self) -> type[AnObjectModel]:
        return AnObjectModel

    async def _get_object(self, context: SubnetContext, client: BittensorPort) -> AnObjectModel:
        self.behave.track("_get_object", context, client)
        return await self.behave.execute("_get_object", context, client)


@pytest.fixture
def context() -> AbstractContext:
    return SubnetContext(NetUid(1))


@pytest.fixture
def update_task(mock_recent_objects_store, mock_bt_contact_pool) -> Task:
    return Task(mock_recent_objects_store, mock_bt_contact_pool)


@pytest.fixture
def executor(update_task, context) -> RecentObjectUpdateTaskExecutor:
    retrying = AsyncRetrying(stop=stop_after_attempt(3))
    return RecentObjectUpdateTaskExecutor(update_task, timeout=12, retrying=retrying, contexts=[context])


@pytest.mark.asyncio
async def test_executor_failed(executor, update_task, mock_bt_client_factory, context):
    async with mock_bt_client_factory() as mock_client:
        async with update_task.behave.mock(_get_object=[Exception("error"), Exception("error"), Exception("error")]):
            await executor.run()

        calls = update_task.behave.calls["_get_object"]
        assert len(calls) == 3
        assert [call[0] for call in calls] == [context] * 3
        assert all(isinstance(call[1], BittensorContactRouter) for call in calls)
        assert all(call[1]._main_contact is mock_client for call in calls)


@pytest.mark.asyncio
async def test_executor_success_after_attempt(
    executor,
    update_task,
    mock_bt_client_factory,
    mock_recent_objects_store,
    context,
):
    object_ = AnObjectModel(field_1="foo", field_2=123)
    timestamp = Timestamp(123123123)

    with time_machine.travel(123_123_123):
        async with mock_bt_client_factory() as mock_client:
            async with (
                update_task.behave.mock(_get_object=[Exception("error"), object_]),
                mock_recent_objects_store.behave.mock(set=[None]),
            ):
                await executor.run()

            data = _CacheEntry(data=object_.model_dump_json(), timestamp=timestamp).model_dump_json()

            calls = update_task.behave.calls["_get_object"]
            assert len(calls) == 2
            assert [call[0] for call in calls] == [context] * 2
            assert all(isinstance(call[1], BittensorContactRouter) for call in calls)
            assert all(call[1]._main_contact is mock_client for call in calls)
            assert mock_recent_objects_store.behave.calls["set"] == [
                (CacheKey(AnObjectModel, NetUid(1), None), data, None)
            ]
