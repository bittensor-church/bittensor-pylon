import pytest
from litestar.stores.base import Store
from tenacity import AsyncRetrying, stop_after_attempt, wait_none

from pylon_client._internal.common.models import BittensorModel
from pylon_client._internal.common.types import Timestamp
from pylon_client.service.bittensor.cache.recent import Scope
from pylon_client.service.bittensor.client import AbstractBittensorClient
from pylon_client.service.bittensor.pool import BittensorClientPool
from pylon_client.service.stores import StoreName
from pylon_client.service.tasks import UpdateRecentObject


class AnObjectModel(BittensorModel):
    field_1: str
    field_2: int


class Task(UpdateRecentObject[AnObjectModel, Scope]):
    _retry = AsyncRetrying(stop=stop_after_attempt(1), wait=wait_none(), reraise=True)

    def __init__(self, store: Store, pool: BittensorClientPool, object_: AnObjectModel) -> None:
        super().__init__(store, pool)
        self._object = object_

    @property
    def _model(self) -> type[AnObjectModel]:
        return AnObjectModel

    async def _get_object(self, scope: Scope, client: AbstractBittensorClient) -> tuple[Timestamp, AnObjectModel]:
        return Timestamp(123456789), self._object

    @classmethod
    def scopes(cls) -> list[Scope]:
        return []


@pytest.fixture
def object_() -> AnObjectModel:
    return AnObjectModel(field_1="test", field_2=123)


@pytest.fixture
def update_task(mock_stores, mock_bt_client_pool, object_) -> UpdateRecentObject[AnObjectModel, Scope]:
    return Task(mock_stores[StoreName.RECENT_OBJECTS], mock_bt_client_pool, object_)
