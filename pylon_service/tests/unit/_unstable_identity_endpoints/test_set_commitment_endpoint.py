"""
Tests for the POST /identity/{identity_name}/subnet/{netuid}/commitments endpoint.
"""

import pytest
from litestar.status_codes import HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_502_BAD_GATEWAY


@pytest.mark.asyncio
async def test_set_commitment_identity_with_0x_prefix(
    identity_test_client_factory, mock_bt_client_factory, snapshot_json
):
    """
    Test setting a commitment with 0x prefix.
    """
    commitment_data = "0x0a0b0c0d0e0f"

    async with mock_bt_client_factory("sn2") as mock_client:
        async with mock_client.mock_behavior(
            set_commitment=[None],
        ):
            async with identity_test_client_factory("sn2") as client:
                response = await client.post(
                    "/api/_unstable/identity/sn2/subnet/2/commitments",
                    json={"commitment": commitment_data},
                )

        assert response.status_code == HTTP_201_CREATED
        assert response.json() == snapshot_json
        assert mock_client.calls["set_commitment"] == [
            (2, bytes.fromhex(commitment_data[2:])),
        ]


@pytest.mark.asyncio
async def test_set_commitment_identity_blockchain_error(
    identity_test_client_factory, mock_bt_client_factory, monkeypatch, snapshot_json
):
    """
    Test that blockchain errors return 502 Bad Gateway after retries exhausted.
    """
    # Set retry attempts to 0 for faster test
    monkeypatch.setattr("pylon_service.api._unstable.tasks.settings.commitment_retry_attempts", 0)

    commitment_data = "0102030405060708"

    async with mock_bt_client_factory("sn1") as mock_client:
        async with mock_client.mock_behavior(
            set_commitment=[RuntimeError("Blockchain connection failed")],
        ):
            async with identity_test_client_factory("sn1") as client:
                response = await client.post(
                    "/api/_unstable/identity/sn1/subnet/1/commitments",
                    json={"commitment": commitment_data},
                )

        assert response.status_code == HTTP_502_BAD_GATEWAY
        assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_set_commitment_identity_retries_on_failure(
    identity_test_client_factory, mock_bt_client_factory, monkeypatch, snapshot_json
):
    """
    Test that set_commitment retries on transient failures and succeeds when blockchain recovers.
    """
    # Set retry attempts to 2 and minimal delay for faster test
    monkeypatch.setattr("pylon_service.api._unstable.tasks.settings.commitment_retry_attempts", 2)
    monkeypatch.setattr("pylon_service.api._unstable.tasks.settings.commitment_retry_delay_seconds", 0.01)

    commitment_data = "0102030405060708"

    async with mock_bt_client_factory("sn1") as mock_client:
        async with mock_client.mock_behavior(
            set_commitment=[
                RuntimeError("First failure"),
                RuntimeError("Second failure"),
                None,  # Third attempt succeeds
            ],
        ):
            async with identity_test_client_factory("sn1") as client:
                response = await client.post(
                    "/api/_unstable/identity/sn1/subnet/1/commitments",
                    json={"commitment": commitment_data},
                )

        assert response.status_code == HTTP_201_CREATED
        assert response.json() == snapshot_json
        # Verify set_commitment was called 3 times (2 failures + 1 success)
        assert len(mock_client.calls["set_commitment"]) == 3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_data",
    [
        pytest.param("not_hex", id="invalid_hex"),
        pytest.param(123, id="invalid_type_int"),
        pytest.param([], id="invalid_type_list"),
        pytest.param("0xGGHH", id="invalid_hex_chars"),
        pytest.param("0xabc", id="odd_length_hex"),
        pytest.param(None, id="none_value"),
        pytest.param("", id="empty_hex_string"),
        pytest.param("0x", id="empty_0x_prefix"),
    ],
)
async def test_set_commitment_identity_invalid_data(identity_test_client_factory, invalid_data, snapshot_json):
    """
    Test setting a commitment with invalid data.
    """
    async with identity_test_client_factory("sn1") as client:
        response = await client.post(
            "/api/_unstable/identity/sn1/subnet/1/commitments",
            json={"commitment": invalid_data},
        )

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_unstable_identity_set_commitment_unknown_identity_returns_404(
    identity_test_client_factory, snapshot_json
):
    async with identity_test_client_factory("sn1") as client:
        response = await client.post(
            "/api/_unstable/identity/unknown/subnet/1/commitments",
            json={"commitment": "0x0102"},
        )

    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json() == snapshot_json
