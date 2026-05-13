"""
Tests for the PUT /subnet/weights endpoint.
"""

import asyncio
import threading

import pytest
from dirty_equals import IsDatetime, IsInt
from litestar.status_codes import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from pylon_commons.models import Block, CommitReveal, SubnetHyperparams
from pylon_commons.types import BlockHash, BlockNumber, MechanismId, NeuronUid, RevealRound
from sqlalchemy import select

from pylon_service.db.database import session_factory
from pylon_service.db.models import TaskStatus, WeightTask
from tests.helpers import db_row_model_dump, wait_for_background_tasks
from tests.integration.localchain.dev_accounts import DevAccount

_EXPECTED_WEIGHTS_TASK = {
    "id": IsInt(ge=0),
    "identity_name": "sn1",
    "weights": {"hotkey1": 0.5, "hotkey2": 0.5},
    "netuid": 1,
    "mechanism_id": 1,
    "hotkey": DevAccount.ALICE.hotkey_ss58,
    "start_block_number": 1000,
    "created_at": IsDatetime(),
    "updated_at": IsDatetime(),
}


@pytest.mark.asyncio
async def test_put_weights_commit_reveal_enabled(
    identity_test_client_factory,
    mock_bt_client_factory,
    snapshot_json,
):
    """
    Test setting weights when commit-reveal is enabled.
    """
    weights = {
        "hotkey1": 0.5,
        "hotkey2": 0.3,
        "hotkey3": 0.2,
    }

    # Set up behaviors that will persist for the background task
    # The background task calls get_latest_block twice (start and during apply)
    async with mock_bt_client_factory("sn1") as mock_client:
        async with mock_client.mock_behavior(
            get_latest_block=[
                Block(number=BlockNumber(1000), hash=BlockHash("0xabc123")),
                Block(number=BlockNumber(1000), hash=BlockHash("0xabc123")),
                Block(number=BlockNumber(1001), hash=BlockHash("0xabc124")),
                Block(number=BlockNumber(1001), hash=BlockHash("0xabc124")),
                Block(number=BlockNumber(1001), hash=BlockHash("0xabc124")),
                Block(number=BlockNumber(1001), hash=BlockHash("0xabc124")),
                Block(number=BlockNumber(1001), hash=BlockHash("0xabc124")),
            ],
            get_hyperparams=[
                SubnetHyperparams(commit_reveal_weights_enabled=CommitReveal.V4),
                SubnetHyperparams(commit_reveal_weights_enabled=CommitReveal.V4),
            ],
            commit_weights=[RevealRound(1005)],
        ):
            async with identity_test_client_factory("sn1") as client:
                response = await client.put(
                    "/api/_unstable/identity/sn1/subnet/1/mechanism/1/weights",
                    json={"weights": weights},
                )

                assert response.status_code == HTTP_200_OK, response.content
                assert response.json() == snapshot_json

                # Wait for the background task to complete
                await wait_for_background_tasks()

        # Verify the commit_weights was called with correct arguments
        assert mock_client.calls["commit_weights"] == [
            (
                1,
                MechanismId(1),
                {
                    NeuronUid(1): 0.5,
                    NeuronUid(2): 0.3,
                    NeuronUid(3): 0.2,
                },
            ),
        ]


@pytest.mark.asyncio
async def test_put_weights_commit_reveal_disabled(
    identity_test_client_factory,
    mock_bt_client_factory,
    snapshot_json,
):
    """
    Test setting weights when commit-reveal is disabled.
    """
    weights = {
        "hotkey1": 0.7,
        "hotkey2": 0.3,
    }

    # Set up behaviors that will persist for the background task
    async with mock_bt_client_factory("sn2") as mock_client:
        async with mock_client.mock_behavior(
            get_latest_block=[
                Block(number=BlockNumber(2000), hash=BlockHash("0xdef456")),
                Block(number=BlockNumber(2000), hash=BlockHash("0xdef456")),
                Block(number=BlockNumber(2000), hash=BlockHash("0xdef456")),
                Block(number=BlockNumber(2000), hash=BlockHash("0xdef456")),
                Block(number=BlockNumber(2000), hash=BlockHash("0xdef456")),
                Block(number=BlockNumber(2000), hash=BlockHash("0xdef456")),
                Block(number=BlockNumber(2000), hash=BlockHash("0xdef456")),
            ],
            get_hyperparams=[
                SubnetHyperparams(commit_reveal_weights_enabled=CommitReveal.DISABLED),
                SubnetHyperparams(commit_reveal_weights_enabled=CommitReveal.DISABLED),
            ],
            set_weights=[None],
        ):
            async with identity_test_client_factory("sn2") as client:
                response = await client.put(
                    "/api/_unstable/identity/sn2/subnet/2/mechanism/1/weights",
                    json={"weights": weights},
                )

                assert response.status_code == HTTP_200_OK, response.content
                assert response.json() == snapshot_json

                # Wait for the background task to complete
                await wait_for_background_tasks()

        # Verify set_weights was called with correct arguments
        assert mock_client.calls["set_weights"] == [
            (
                2,
                MechanismId(1),
                {
                    NeuronUid(1): 0.7,
                    NeuronUid(2): 0.3,
                },
            ),
        ]


@pytest.mark.asyncio
async def test_put_weights_retries_when_prepare_fails(
    identity_test_client_factory,
    mock_bt_client_factory,
    monkeypatch: pytest.MonkeyPatch,
    snapshot_json,
):
    monkeypatch.setattr("pylon_service.settings.settings.weights_retry_attempts", 3)
    monkeypatch.setattr("pylon_service.settings.settings.weights_retry_delay_seconds", 0)

    weights = {"hotkey1": 0.5, "hotkey2": 0.5}

    async with mock_bt_client_factory("sn1") as mock_client:
        async with mock_client.mock_behavior(
            get_latest_block=[
                RuntimeError("Network error"),
                RuntimeError("Network error"),
                Block(number=BlockNumber(1000), hash=BlockHash("0xabc123")),
                Block(number=BlockNumber(1000), hash=BlockHash("0xabc123")),
                Block(number=BlockNumber(1000), hash=BlockHash("0xabc123")),
                Block(number=BlockNumber(1000), hash=BlockHash("0xabc123")),
                Block(number=BlockNumber(1000), hash=BlockHash("0xabc123")),
            ],
            get_hyperparams=[
                SubnetHyperparams(commit_reveal_weights_enabled=CommitReveal.DISABLED),
                SubnetHyperparams(commit_reveal_weights_enabled=CommitReveal.DISABLED),
            ],
            set_weights=[None],
        ):
            async with identity_test_client_factory("sn1") as client:
                response = await client.put(
                    "/api/_unstable/identity/sn1/subnet/1/mechanism/1/weights",
                    json={"weights": weights},
                )

                assert response.status_code == HTTP_200_OK, response.content
                assert response.json() == snapshot_json

                await wait_for_background_tasks()

        assert len(mock_client.calls["get_latest_block"]) == 7
        assert mock_client.calls["set_weights"] == [
            (
                1,
                MechanismId(1),
                {
                    NeuronUid(1): 0.5,
                    NeuronUid(2): 0.5,
                },
            )
        ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "json_data",
    [
        pytest.param(
            {},
            id="missing_weights_field",
        ),
        pytest.param(
            {"weights": {}},
            id="empty_weights",
        ),
        pytest.param(
            {"weights": {"hotkey1": "invalid"}},
            id="invalid_weight_value",
        ),
        pytest.param(
            {"weights": {"": 0.5}},
            id="empty_hotkey",
        ),
    ],
)
async def test_put_weights_validation_errors(identity_test_client_factory, json_data: dict, snapshot_json):
    """
    Test that invalid weight data fails validation.
    """
    async with identity_test_client_factory("sn1") as client:
        response = await client.put(
            "/api/_unstable/identity/sn1/subnet/1/mechanism/1/weights",
            json=json_data,
        )

    assert response.status_code == HTTP_400_BAD_REQUEST, response.content
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_unstable_identity_put_weights_unknown_identity_returns_404(identity_test_client_factory, snapshot_json):
    async with identity_test_client_factory("sn1") as client:
        response = await client.put(
            "/api/_unstable/identity/unknown/subnet/1/mechanism/1/weights",
            json={"weights": {"hotkey1": 1.0}},
        )

    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_put_weights_stores_running_weight_task(
    identity_test_client_factory,
    mock_bt_client_factory,
    clean_weight_tasks_db_table,
):
    task_reached_weight_submission = threading.Event()
    unblock_weight_submission = threading.Event()

    async def blocking_set_weights(*args, **kwargs):
        task_reached_weight_submission.set()
        await asyncio.to_thread(unblock_weight_submission.wait)
        return None

    async with mock_bt_client_factory("sn1") as mock_client:
        async with mock_client.mock_behavior(
            set_weights=[blocking_set_weights],
        ):
            async with identity_test_client_factory("sn1") as client:
                await clean_weight_tasks_db_table()
                response = await client.put(
                    "/api/_unstable/identity/sn1/subnet/1/mechanism/1/weights",
                    json={"weights": _EXPECTED_WEIGHTS_TASK["weights"]},
                )

                assert response.status_code == 200

                await asyncio.to_thread(task_reached_weight_submission.wait, 1)

                async with session_factory() as session:
                    result = await session.scalars(select(WeightTask))
                    tasks = list(result)

                assert len(tasks) == 1

                task = tasks[0]
                assert db_row_model_dump(task) == {
                    **_EXPECTED_WEIGHTS_TASK,
                    "status": TaskStatus.RUNNING,
                }

                unblock_weight_submission.set()
                await wait_for_background_tasks()


@pytest.mark.asyncio
async def test_put_weights_stores_succeeded_weight_task(
    identity_test_client_factory,
    mock_bt_client_factory,
    clean_weight_tasks_db_table,
):
    async with mock_bt_client_factory("sn1") as mock_client:
        async with mock_client.mock_behavior():
            async with identity_test_client_factory("sn1") as client:
                await clean_weight_tasks_db_table()
                response = await client.put(
                    "/api/_unstable/identity/sn1/subnet/1/mechanism/1/weights",
                    json={"weights": _EXPECTED_WEIGHTS_TASK["weights"]},
                )

                assert response.status_code == 200

                await wait_for_background_tasks()

                async with session_factory() as session:
                    result = await session.scalars(select(WeightTask))
                    tasks = list(result)

                assert len(tasks) == 1

                task = tasks[0]
                assert db_row_model_dump(task) == {
                    **_EXPECTED_WEIGHTS_TASK,
                    "status": TaskStatus.SUCCEEDED,
                }


@pytest.mark.asyncio
async def test_put_weights_stores_failed_weight_task(
    identity_test_client_factory,
    mock_bt_client_factory,
    clean_weight_tasks_db_table,
    monkeypatch,
):
    monkeypatch.setattr("pylon_service.settings.settings.weights_retry_attempts", 0)

    async with mock_bt_client_factory("sn1") as mock_client:
        async with mock_client.mock_behavior(set_weights=[RuntimeError("Network error")]):
            async with identity_test_client_factory("sn1") as client:
                await clean_weight_tasks_db_table()
                response = await client.put(
                    "/api/_unstable/identity/sn1/subnet/1/mechanism/1/weights",
                    json={"weights": _EXPECTED_WEIGHTS_TASK["weights"]},
                )

                assert response.status_code == 200

                await wait_for_background_tasks()

                async with session_factory() as session:
                    result = await session.scalars(select(WeightTask))
                    tasks = list(result)

                assert len(tasks) == 1

                task = tasks[0]
                assert task.status == TaskStatus.FAILED


@pytest.mark.asyncio
async def test_put_weights_stores_expired_weight_task(
    identity_test_client_factory,
    mock_bt_client_factory,
    clean_weight_tasks_db_table,
    monkeypatch,
):
    monkeypatch.setattr("pylon_service.settings.settings.weights_retry_delay_seconds", 0)

    current_block_number = 1000

    async def get_latest_block_mock(*args, **kwargs):
        return Block(number=BlockNumber(current_block_number), hash=BlockHash("0xabc123"))

    async def set_weights_mock(*args, **kwargs):
        nonlocal current_block_number
        current_block_number += 1000
        raise RuntimeError("Network error")

    async with mock_bt_client_factory("sn1") as mock_client:
        async with mock_client.mock_behavior(
            get_latest_block=[get_latest_block_mock] * 20, set_weights=[set_weights_mock, None]
        ):
            async with identity_test_client_factory("sn1") as client:
                await clean_weight_tasks_db_table()
                response = await client.put(
                    "/api/_unstable/identity/sn1/subnet/1/mechanism/1/weights",
                    json={"weights": _EXPECTED_WEIGHTS_TASK["weights"]},
                )

                assert response.status_code == 200

                await wait_for_background_tasks()

                async with session_factory() as session:
                    result = await session.scalars(select(WeightTask))
                    tasks = list(result)

                assert len(tasks) == 1

                task = tasks[0]
                assert task.status == TaskStatus.EXPIRED


@pytest.mark.asyncio
async def test_put_weights_stores_cancelled_weight_task(
    identity_test_client_factory,
    mock_bt_client_factory,
    clean_weight_tasks_db_table,
):
    task_reached_weight_submission = threading.Event()
    unblock_weight_submission = threading.Event()

    async def blocking_set_weights(*args, **kwargs):
        task_reached_weight_submission.set()
        await asyncio.to_thread(unblock_weight_submission.wait)
        return None

    async with mock_bt_client_factory("sn1") as mock_client:
        async with mock_client.mock_behavior(
            set_weights=[blocking_set_weights, None],
        ):
            async with identity_test_client_factory("sn1") as client:
                await clean_weight_tasks_db_table()
                response = await client.put(
                    "/api/_unstable/identity/sn1/subnet/1/mechanism/1/weights",
                    json={"weights": {"other_hotkey": 0.5}},
                )

                assert response.status_code == 200

                await asyncio.to_thread(task_reached_weight_submission.wait, 1)

                response = await client.put(
                    "/api/_unstable/identity/sn1/subnet/1/mechanism/1/weights",
                    json={"weights": _EXPECTED_WEIGHTS_TASK["weights"]},
                )

                assert response.status_code == 200

                unblock_weight_submission.set()
                await wait_for_background_tasks()

                async with session_factory() as session:
                    result = await session.scalars(select(WeightTask))
                    tasks = list(result)

                assert len(tasks) == 2

                assert sum(task.status == TaskStatus.CANCELLED for task in tasks) == 1

                cancelled_task = next(task for task in tasks if task.status == TaskStatus.CANCELLED)
                assert "other_hotkey" in cancelled_task.weights
