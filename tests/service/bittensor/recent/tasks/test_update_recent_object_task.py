import pytest
from litestar.stores.base import Store

from pylon_client._internal.common.models import BittensorModel
from pylon_client._internal.common.types import NetUid, Timestamp
from pylon_client.service.bittensor.client import AbstractBittensorClient
from pylon_client.service.bittensor.pool import BittensorClientPool
from pylon_client.service.bittensor.recent import SubnetContext
from pylon_client.service.bittensor.recent.adapter import CacheKey, _CacheEntry
from pylon_client.service.bittensor.recent.tasks import UpdateRecentObject


class AnObjectModel(BittensorModel):
    field_1: str
    field_2: int


class Task(UpdateRecentObject[AnObjectModel, SubnetContext]):
    def __init__(self, store: Store, pool: BittensorClientPool, object_: AnObjectModel) -> None:
        super().__init__(store, pool)
        self._object = object_

    @property
    def _model(self) -> type[AnObjectModel]:
        return AnObjectModel

    async def _get_object(
        self, context: SubnetContext, client: AbstractBittensorClient
    ) -> tuple[Timestamp, AnObjectModel]:
        return Timestamp(123123123), self._object

    @classmethod
    def contexts(cls) -> list[SubnetContext]:
        return []


@pytest.fixture
def object_() -> AnObjectModel:
    return AnObjectModel(field_1="test", field_2=123)


@pytest.fixture
def update_task(mock_recent_objects_store, mock_bt_client_pool, object_) -> Task:
    return Task(mock_recent_objects_store, mock_bt_client_pool, object_)


@pytest.mark.asyncio
async def test_execute(mock_recent_objects_store, update_task, object_):
    context = SubnetContext(NetUid(1))
    async with mock_recent_objects_store.behave.mock(set=[None]):
        await update_task.execute(context)

    data = _CacheEntry(data=object_.model_dump_json(), timestamp=Timestamp(123123123)).model_dump_json()
    assert mock_recent_objects_store.behave.calls["set"] == [(CacheKey(AnObjectModel, NetUid(1), None), data, None)]
