"""
Tests for the PUT /subnet/weights endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from pylon_commons.models import Block, CommitReveal, SubnetHyperparams
from pylon_commons.types import BlockHash, BlockNumber, MechanismId, NeuronUid, RevealRound

from pylon_service.api._unstable.tasks import ApplyWeights
from tests.helpers import wait_for_background_tasks


@pytest.mark.parametrize(
    "mechanism_url_infix,expected_mechanism_id",
    [
        pytest.param("", 0, id="no_mechanism_id"),
        pytest.param("mechanism/1/", 1, id="with_mechanism_id"),
    ],
)
@pytest.mark.asyncio
async def test_put_weights_commit_reveal_enabled(
    mechanism_url_infix: str,
    expected_mechanism_id: int,
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
                    f"/api/_unstable/identity/sn1/subnet/1/{mechanism_url_infix}weights",
                    json={"weights": weights},
                )

                assert response.status_code == HTTP_200_OK, response.content
                assert response.json() == snapshot_json

                # Wait for the background task to complete
                await wait_for_background_tasks(ApplyWeights.tasks_running)

        # Verify the commit_weights was called with correct arguments
        assert mock_client.calls["commit_weights"] == [
            (
                1,
                MechanismId(expected_mechanism_id),
                {
                    NeuronUid(1): 0.5,
                    NeuronUid(2): 0.3,
                    NeuronUid(3): 0.2,
                },
            ),
        ]


@pytest.mark.parametrize(
    "mechanism_url_infix,expected_mechanism_id",
    [
        pytest.param("", 0, id="no_mechanism_id"),
        pytest.param("mechanism/1/", 1, id="with_mechanism_id"),
    ],
)
@pytest.mark.asyncio
async def test_put_weights_commit_reveal_disabled(
    mechanism_url_infix: str,
    expected_mechanism_id: int,
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
                    f"/api/_unstable/identity/sn2/subnet/2/{mechanism_url_infix}weights",
                    json={"weights": weights},
                )

                assert response.status_code == HTTP_200_OK, response.content
                assert response.json() == snapshot_json

                # Wait for the background task to complete
                await wait_for_background_tasks(ApplyWeights.tasks_running)

        # Verify set_weights was called with correct arguments
        assert mock_client.calls["set_weights"] == [
            (
                2,
                MechanismId(expected_mechanism_id),
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
                    "/api/_unstable/identity/sn1/subnet/1/weights",
                    json={"weights": weights},
                )

                assert response.status_code == HTTP_200_OK, response.content
                assert response.json() == snapshot_json

                await wait_for_background_tasks(ApplyWeights.tasks_running)

        assert len(mock_client.calls["get_latest_block"]) == 9
        assert mock_client.calls["set_weights"] == [
            (
                1,
                MechanismId(0),
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
            "/api/_unstable/identity/sn1/subnet/1/weights",
            json=json_data,
        )

    assert response.status_code == HTTP_400_BAD_REQUEST, response.content
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_unstable_identity_put_weights_unknown_identity_returns_404(identity_test_client_factory, snapshot_json):
    async with identity_test_client_factory("sn1") as client:
        response = await client.put(
            "/api/_unstable/identity/unknown/subnet/1/weights",
            json={"weights": {"hotkey1": 1.0}},
        )

    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json() == snapshot_json
