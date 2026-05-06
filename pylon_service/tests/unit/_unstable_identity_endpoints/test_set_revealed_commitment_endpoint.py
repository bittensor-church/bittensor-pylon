import pytest
from litestar.status_codes import HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_502_BAD_GATEWAY


@pytest.mark.asyncio
async def test_set_revealed_commitment_identity_success(
    identity_test_client_factory, mock_bt_client_factory, snapshot_json
):
    async with mock_bt_client_factory("sn1") as mock_client:
        async with mock_client.mock_behavior(set_revealed_commitment=[321]):
            async with identity_test_client_factory("sn1") as client:
                response = await client.post(
                    "/api/_unstable/identity/sn1/subnet/1/commitments/revealed",
                    json={"commitment": "model-a", "blocks_until_reveal": 12},
                )

        assert response.status_code == HTTP_201_CREATED
        assert response.json() == snapshot_json
        assert mock_client.calls["set_revealed_commitment"] == [
            (1, "model-a", 12),
        ]


@pytest.mark.asyncio
async def test_set_revealed_commitment_identity_retries_on_failure(
    identity_test_client_factory, mock_bt_client_factory, monkeypatch, snapshot_json
):
    monkeypatch.setattr("pylon_service.api._unstable.tasks.settings.commitment_retry_attempts", 2)
    monkeypatch.setattr("pylon_service.api._unstable.tasks.settings.commitment_retry_delay_seconds", 0.01)

    async with mock_bt_client_factory("sn1") as mock_client:
        async with mock_client.mock_behavior(
            set_revealed_commitment=[RuntimeError("First failure"), RuntimeError("Second failure"), 654]
        ):
            async with identity_test_client_factory("sn1") as client:
                response = await client.post(
                    "/api/_unstable/identity/sn1/subnet/1/commitments/revealed",
                    json={"commitment": "model-a", "blocks_until_reveal": 12},
                )

        assert response.status_code == HTTP_201_CREATED
        assert response.json() == snapshot_json
        assert mock_client.calls["set_revealed_commitment"] == [
            (1, "model-a", 12),
            (1, "model-a", 12),
            (1, "model-a", 12),
        ]


@pytest.mark.asyncio
async def test_set_revealed_commitment_identity_blockchain_error(
    identity_test_client_factory, mock_bt_client_factory, monkeypatch, snapshot_json
):
    monkeypatch.setattr("pylon_service.api._unstable.tasks.settings.commitment_retry_attempts", 0)

    async with mock_bt_client_factory("sn1") as mock_client:
        async with mock_client.mock_behavior(set_revealed_commitment=[RuntimeError("Blockchain connection failed")]):
            async with identity_test_client_factory("sn1") as client:
                response = await client.post(
                    "/api/_unstable/identity/sn1/subnet/1/commitments/revealed",
                    json={"commitment": "model-a", "blocks_until_reveal": 12},
                )

        assert response.status_code == HTTP_502_BAD_GATEWAY
        assert response.json() == snapshot_json


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"commitment": 123, "blocks_until_reveal": 12}, id="invalid_commitment_type"),
        pytest.param({"commitment": "model-a", "blocks_until_reveal": "soon"}, id="invalid_blocks"),
    ],
)
async def test_set_revealed_commitment_identity_invalid_data(
    identity_test_client_factory, payload: dict[str, object], snapshot_json
):
    async with identity_test_client_factory("sn1") as client:
        response = await client.post(
            "/api/_unstable/identity/sn1/subnet/1/commitments/revealed",
            json=payload,
        )

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_unstable_identity_set_revealed_commitment_unknown_identity_returns_404(
    identity_test_client_factory, snapshot_json
):
    async with identity_test_client_factory("sn1") as client:
        response = await client.post(
            "/api/_unstable/identity/unknown/subnet/1/commitments/revealed",
            json={"commitment": "model-a", "blocks_until_reveal": 12},
        )

    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json() == snapshot_json
