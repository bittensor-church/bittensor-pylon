import pytest

from pylon._internal.background.queue import AsyncioQueue, Task


@pytest.fixture
def queue() -> AsyncioQueue:
    return AsyncioQueue()


@pytest.fixture
def task() -> Task:
    return Task(name="test_task", args=(1, 2), kwargs={"key": "value"})


@pytest.mark.asyncio
@pytest.mark.parametrize("timeout", (1.0, -1.0))
async def test_put_and_get(queue, task, timeout):
    await queue.put(task)
    result = await queue.get(timeout=timeout)
    assert result == task


@pytest.mark.asyncio
@pytest.mark.parametrize("timeout", (1.0, -1.0))
async def test_get_empty(queue, timeout):
    result = await queue.get(timeout=timeout)
    assert result is None


@pytest.mark.asyncio
async def test_queue_empty(queue, task):
    assert queue.empty() is True

    await queue.put(task)
    assert queue.empty() is False

    await queue.get(timeout=1.0)
    await queue.task_done()
    assert queue.empty() is True


@pytest.mark.asyncio
async def test_task_done(queue, task):
    await queue.put(task)
    await queue.get(timeout=1.0)
    await queue.task_done()
    with pytest.raises(ValueError):
        await queue.task_done()
