import asyncio
import logging
from unittest.mock import call, create_autospec

import pytest

from pylon._internal.background.processor import TaskProcessor
from pylon._internal.background.scheduler import TaskScheduler


@pytest.fixture
def processor():
    processor = create_autospec(TaskProcessor, spec_set=True, instance=True)
    return processor


@pytest.fixture
def scheduler(processor):
    return TaskScheduler(processor, interval=0.1, task_name="test_task")


@pytest.mark.asyncio
async def test_start(scheduler, caplog):
    caplog.set_level(logging.INFO)

    await scheduler.start()

    assert caplog.messages[-1] == "Starting scheduler for task. task_name: 'test_task', interval: 0.1"
    assert scheduler._task is not None


@pytest.mark.asyncio
async def test_start_already_running(scheduler):
    await scheduler.start()
    with pytest.raises(RuntimeError, match="Task scheduler is already running"):
        await scheduler.start()


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_scheduling(scheduler, processor):
    await scheduler.start()
    await asyncio.sleep(0.35)  # Should execute ~3 times
    await scheduler.stop()

    assert processor.submit.call_count == 3
    assert processor.submit.mock_calls == [
        call("test_task", args=None, kwargs=None),
        call("test_task", args=None, kwargs=None),
        call("test_task", args=None, kwargs=None),
    ]


@pytest.mark.asyncio
async def test_scheduling_eager(scheduler, processor):
    scheduler._eager = True

    await scheduler.start()
    await asyncio.sleep(0.35)
    await scheduler.stop()

    assert processor.submit.call_count == 4


@pytest.mark.asyncio
async def test_stop(processor):
    scheduler = TaskScheduler(processor, interval=0.1, task_name="test_task")

    await scheduler.start()
    await asyncio.sleep(0.35)
    await scheduler.stop()
    await asyncio.sleep(0.5)  # should not schedule anymore

    assert processor.submit.call_count == 3
    assert scheduler._task is None
