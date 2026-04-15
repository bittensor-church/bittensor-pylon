import pytest
from litestar.status_codes import HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_502_BAD_GATEWAY
from litestar.testing import AsyncTestClient

from pylon_service.bittensor.mock_contact import MockBittensorContact


@pytest.mark.asyncio
async def test_v1_identity_set_revealed_commitment_success(
    test_client: AsyncTestClient, sn1_mock_bt_client: MockBittensorContact, snapshot_json
):
    async with sn1_mock_bt_client.mock_behavior(set_revealed_commitment=[321]):
        response = await test_client.post(
            "/api/v1/identity/sn1/subnet/1/commitments/revealed",
            json={"commitment": "model-a", "blocks_until_reveal": 12, "block_time": 12},
        )

    assert response.status_code == HTTP_201_CREATED
    assert response.json() == snapshot_json
    assert sn1_mock_bt_client.calls["set_revealed_commitment"] == [
        (1, "model-a", 12, 12),
    ]


@pytest.mark.asyncio
async def test_v1_identity_set_revealed_commitment_retries_on_failure(
    test_client: AsyncTestClient, sn1_mock_bt_client: MockBittensorContact, monkeypatch, snapshot_json
):
    monkeypatch.setattr("pylon_service.api._unstable.tasks.settings.commitment_retry_attempts", 2)
    monkeypatch.setattr("pylon_service.api._unstable.tasks.settings.commitment_retry_delay_seconds", 0.01)

    async with sn1_mock_bt_client.mock_behavior(
        set_revealed_commitment=[RuntimeError("First failure"), RuntimeError("Second failure"), 654]
    ):
        response = await test_client.post(
            "/api/v1/identity/sn1/subnet/1/commitments/revealed",
            json={"commitment": "model-a", "blocks_until_reveal": 12, "block_time": 12},
        )

    assert response.status_code == HTTP_201_CREATED
    assert response.json() == snapshot_json
    assert sn1_mock_bt_client.calls["set_revealed_commitment"] == [
        (1, "model-a", 12, 12),
        (1, "model-a", 12, 12),
        (1, "model-a", 12, 12),
    ]


@pytest.mark.asyncio
async def test_v1_identity_set_revealed_commitment_blockchain_error(
    test_client: AsyncTestClient, sn1_mock_bt_client: MockBittensorContact, monkeypatch, snapshot_json
):
    monkeypatch.setattr("pylon_service.api._unstable.tasks.settings.commitment_retry_attempts", 0)

    async with sn1_mock_bt_client.mock_behavior(set_revealed_commitment=[RuntimeError("Blockchain connection failed")]):
        response = await test_client.post(
            "/api/v1/identity/sn1/subnet/1/commitments/revealed",
            json={"commitment": "model-a", "blocks_until_reveal": 12, "block_time": 12},
        )

    assert response.status_code == HTTP_502_BAD_GATEWAY
    assert response.json() == snapshot_json


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"commitment": 123, "blocks_until_reveal": 12, "block_time": 12}, id="invalid_commitment_type"),
        pytest.param({"commitment": "model-a", "blocks_until_reveal": "soon", "block_time": 12}, id="invalid_blocks"),
        pytest.param({"commitment": "model-a", "blocks_until_reveal": 12}, id="missing_block_time"),
    ],
)
async def test_v1_identity_set_revealed_commitment_invalid_data(
    test_client: AsyncTestClient, payload: dict[str, object], snapshot_json
):
    response = await test_client.post(
        "/api/v1/identity/sn1/subnet/1/commitments/revealed",
        json=payload,
    )

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_v1_identity_set_revealed_commitment_unknown_identity_returns_404(
    test_client: AsyncTestClient, snapshot_json
):
    response = await test_client.post(
        "/api/v1/identity/unknown/subnet/1/commitments/revealed",
        json={"commitment": "model-a", "blocks_until_reveal": 12, "block_time": 12},
    )

    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json() == snapshot_json
