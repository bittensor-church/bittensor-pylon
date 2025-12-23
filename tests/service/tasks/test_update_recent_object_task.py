import pytest
from tenacity import AsyncRetrying, stop_after_attempt, wait_none

from pylon._internal.common.models import BittensorModel, Block
from pylon._internal.common.types import NetUid, Timestamp
from pylon.service.bittensor.cache.recent import _RecentCacheEntry
from pylon.service.tasks import UpdateRecentObject
from tests.factories import BlockFactory


class AnObjectModel(BittensorModel):
    field_1: str
    field_2: int


@pytest.fixture
def object_() -> AnObjectModel:
    return AnObjectModel(field_1="test", field_2=123)


@pytest.fixture
def update_task(mock_store, open_access_mock_bt_client, object_) -> UpdateRecentObject[AnObjectModel]:
    class Task(UpdateRecentObject[AnObjectModel]):
        _Retry = AsyncRetrying(stop=stop_after_attempt(1), wait=wait_none(), reraise=True)

        @property
        def model(self) -> type[AnObjectModel]:
            return AnObjectModel

        async def _get_object(self, block: Block) -> AnObjectModel:
            return object_

    return Task(NetUid(1), mock_store, open_access_mock_bt_client)


@pytest.mark.asyncio
async def test_execute_failed_to_get_block(update_task, behave, open_access_mock_bt_client):
    async with open_access_mock_bt_client.mock_behavior(get_latest_block=[Exception("Error")]):
        await update_task.execute()

    assert open_access_mock_bt_client.calls == {"get_latest_block": [()]}
    assert behave.calls == {}


@pytest.mark.asyncio
async def test_execute_failed_to_get_timestamp(
    update_task, behave, open_access_mock_bt_client, block_factory: BlockFactory
):
    block = block_factory.build()
    async with open_access_mock_bt_client.mock_behavior(
        get_latest_block=[block],
        get_block_timestamp=[Exception("Error")],
    ):
        await update_task.execute()

    assert open_access_mock_bt_client.calls == {"get_latest_block": [()], "get_block_timestamp": [(block,)]}
    assert behave.calls == {}


@pytest.mark.asyncio
async def test_execute_success(
    update_task,
    behave,
    open_access_mock_bt_client,
    block_factory,
    object_,
):
    timestamp = Timestamp(123456789)
    block = block_factory.build()
    async with (
        open_access_mock_bt_client.mock_behavior(
            get_latest_block=[block],
            get_block_timestamp=[timestamp],
        ),
        behave.mock(set=[None]),
    ):
        await update_task.execute()

    assert open_access_mock_bt_client.calls == {"get_latest_block": [()], "get_block_timestamp": [(block,)]}
    assert behave.calls["set"] == [
        (
            "recent_AnObjectModel_1",
            _RecentCacheEntry(timestamp=timestamp, entry=object_).model_dump_json(),
            None,
        )
    ]
