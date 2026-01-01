import pytest
from litestar.stores.base import Store
from tenacity import AsyncRetrying, stop_after_attempt

from pylon_client._internal.common.models import BittensorModel
from pylon_client._internal.common.types import NetUid, Timestamp
from pylon_client.service.bittensor.client import AbstractBittensorClient
from pylon_client.service.bittensor.pool import BittensorClientPool
from pylon_client.service.bittensor.recent import AbstractContext, RecentObjectUpdateTaskExecutor, SubnetContext
from pylon_client.service.bittensor.recent.adapter import CacheKey, _CacheEntry
from pylon_client.service.bittensor.recent.tasks import UpdateRecentObject
from tests.behave import Behave


class AnObjectModel(BittensorModel):
    field_1: str
    field_2: int


class Task(UpdateRecentObject[AnObjectModel, SubnetContext]):
    def __init__(self, store: Store, pool: BittensorClientPool) -> None:
        super().__init__(store, pool)
        self.behave = Behave()

    @property
    def _model(self) -> type[AnObjectModel]:
        return AnObjectModel

    async def _get_object(
        self, context: SubnetContext, client: AbstractBittensorClient
    ) -> tuple[Timestamp, AnObjectModel]:
        self.behave.track("_get_object", context, client)
        return await self.behave.execute("_get_object", context, client)


@pytest.fixture
def context() -> AbstractContext:
    return SubnetContext(NetUid(1))


@pytest.fixture
def update_task(mock_recent_objects_store, mock_bt_client_pool) -> Task:
    return Task(mock_recent_objects_store, mock_bt_client_pool)


@pytest.fixture
def executor(update_task, context) -> RecentObjectUpdateTaskExecutor:
    retrying = AsyncRetrying(stop=stop_after_attempt(3))
    return RecentObjectUpdateTaskExecutor(update_task, timeout=12, retrying=retrying, contexts=[context])


@pytest.mark.asyncio
async def test_executor_failed(executor, update_task, open_access_mock_bt_client, context):
    async with update_task.behave.mock(_get_object=[Exception("error"), Exception("error"), Exception("error")]):
        await executor.run()

    assert update_task.behave.calls["_get_object"] == [(context, open_access_mock_bt_client)] * 3


@pytest.mark.asyncio
async def test_executor_success_after_attempt(
    executor,
    update_task,
    open_access_mock_bt_client,
    mock_recent_objects_store,
    context,
):
    object_ = AnObjectModel(field_1="foo", field_2=123)

    async with (
        update_task.behave.mock(_get_object=[Exception("error"), (Timestamp(123123123), object_)]),
        mock_recent_objects_store.behave.mock(set=[None]),
    ):
        await executor.run()

    data = _CacheEntry(data=object_.model_dump_json(), timestamp=Timestamp(123123123)).model_dump_json()

    assert update_task.behave.calls["_get_object"] == [(context, open_access_mock_bt_client)] * 2
    assert mock_recent_objects_store.behave.calls["set"] == [(CacheKey(AnObjectModel, NetUid(1), None), data, None)]
