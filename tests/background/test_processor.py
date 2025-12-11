import asyncio
from collections.abc import Callable

import pytest

from pylon._internal.background.processor import TaskProcessor
from pylon._internal.background.queue import AsyncioQueue


@pytest.fixture
def queue() -> AsyncioQueue:
    # AsyncioQueue is already an in-memory implementation, we don't need another mock queue for tests.
    return AsyncioQueue()


@pytest.fixture
def processor(queue) -> TaskProcessor:
    return TaskProcessor(queue, workers=1, timeout=1)


@pytest.fixture
def make_task(processor) -> Callable:
    """
    This fixture uses a processor and returns a callable that can be called to register a task.
    Created task can be used to detect if the task was actually executed or not. It modifies a mutable
    data structure (list of int) to indicate whether the task was executed or not.
    """

    def _maker(
        name: str,
        timeout: float | None = None,
        litmus: list[int] | None = None,
        wait: float = 0,
    ) -> Callable:
        @processor.register(name, timeout=timeout)
        async def litmus_task(x: int | None = None):
            await asyncio.sleep(wait)
            if litmus is not None and x is not None:
                litmus.append(x)

        return litmus_task

    return _maker


@pytest.mark.asyncio
async def test_register_task(processor, make_task):
    task1 = make_task("test_task_1")
    task2 = make_task("test_task_2", timeout=10)

    assert "test_task_1" in processor._registered_tasks
    assert "test_task_2" in processor._registered_tasks
    assert processor._registered_tasks["test_task_1"][0] is None
    assert processor._registered_tasks["test_task_1"][1] is task1
    assert processor._registered_tasks["test_task_2"][0] == 10
    assert processor._registered_tasks["test_task_2"][1] is task2


@pytest.mark.asyncio
async def test_register_override_task_registration(processor, make_task, caplog):
    task1 = make_task("test_task")
    task2 = make_task("test_task", timeout=10.0)

    assert "test_task" in processor._registered_tasks
    assert processor._registered_tasks["test_task"][0] == 10.0
    assert processor._registered_tasks["test_task"][1] is not task1
    assert processor._registered_tasks["test_task"][1] is task2

    assert caplog.messages[-1] == "Task already registered, overriding existing task. task_name: test_task"


@pytest.mark.asyncio
async def test_start_already_running(processor):
    await processor.start()
    with pytest.raises(RuntimeError, match="Task processor is already running"):
        await processor.start()


@pytest.mark.asyncio
async def test_start(processor, caplog):
    await processor.start()
    await asyncio.sleep(1)

    assert processor._running is True
    assert len(processor._workers) == 1


@pytest.mark.asyncio
async def test_submit_unregistered_task(processor):
    await processor.start()

    with pytest.raises(ValueError, match="Task is not registered"):
        await processor.submit("nonexistent_task")

    await processor.stop()


@pytest.mark.asyncio
async def test_submit_without_start(processor, make_task, caplog):
    make_task("test_task")
    await processor.submit("test_task")
    assert caplog.messages[-1] == "Cannot submit task, task processor is not running."


@pytest.mark.asyncio
async def test_execute_task(processor, make_task):
    litmus = []
    make_task("test_task", litmus=litmus)

    await processor.start()
    await processor.submit("test_task", args=(42,))
    await asyncio.sleep(1)
    await processor.stop()

    assert litmus == [42]


@pytest.mark.asyncio
async def test_execute_task_with_timeout(processor, make_task, caplog):
    litmus = []
    make_task("test_task", litmus=litmus, timeout=1, wait=2)

    await processor.start()
    await processor.submit("test_task", args=(42,))
    await asyncio.sleep(1)
    await processor.stop()

    assert litmus == []


@pytest.mark.asyncio
async def test_task_exception_handling(processor, make_task, caplog):
    bad_litmus = 10  # cannot append to int so it'll raise
    good_litmus = []

    make_task("failing_task", litmus=bad_litmus)
    make_task("success_task", litmus=good_litmus)

    await processor.start()

    await processor.submit("failing_task", args=(42,))
    await asyncio.sleep(1)

    assert caplog.messages[-1] == (
        "Worker failed with error while executing task. worker_id: 1, task: failing_task, "
        "error: 'int' object has no attribute 'append'"
    )

    await processor.submit("success_task", args=(42,))
    await asyncio.sleep(1)

    assert good_litmus == [42]  # still working

    await processor.stop()


@pytest.mark.asyncio
async def test_stop_with_graceful_shutdown(processor, make_task):
    litmus = []

    make_task("test_task", litmus=litmus, wait=0.1)

    await processor.start()
    for i in range(5):
        await processor.submit("test_task", args=(i,))

    await processor.stop(timeout=10.0)

    assert litmus == [0, 1, 2, 3, 4]
    assert processor._running is False
    assert processor._workers == []


@pytest.mark.asyncio
async def test_stop_with_task_cancellation(processor, make_task, caplog):
    litmus = []
    make_task("test_task", litmus=litmus)
    make_task("slow_task", litmus=litmus, wait=10.0)

    await processor.start()
    await processor.submit("test_task", args=(10,))
    await processor.submit("slow_task", args=(20,))

    await processor.stop(timeout=1.0)

    assert litmus == [10]
