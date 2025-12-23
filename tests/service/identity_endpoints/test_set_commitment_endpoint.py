"""
Tests for the POST /identity/{identity_name}/subnet/{netuid}/commitments endpoint.
"""

import pytest
from litestar.status_codes import HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_502_BAD_GATEWAY
from litestar.testing import AsyncTestClient

from tests.mock_bittensor_client import MockBittensorClient


@pytest.mark.asyncio
async def test_set_commitment_identity_success(test_client: AsyncTestClient, sn1_mock_bt_client: MockBittensorClient):
    """
    Test setting a commitment successfully.
    """
    commitment_data = "0102030405060708"

    async with sn1_mock_bt_client.mock_behavior(
        set_commitment=[None],
    ):
        response = await test_client.post(
            "/api/v1/identity/sn1/subnet/1/commitments",
            json={"commitment": commitment_data},
        )

    assert response.status_code == HTTP_201_CREATED
    assert response.json() == {
        "detail": "Commitment set successfully.",
    }
    assert sn1_mock_bt_client.calls["set_commitment"] == [
        (1, bytes.fromhex(commitment_data)),
    ]


@pytest.mark.asyncio
async def test_set_commitment_identity_with_0x_prefix(
    test_client: AsyncTestClient, sn2_mock_bt_client: MockBittensorClient
):
    """
    Test setting a commitment with 0x prefix.
    """
    commitment_data = "0x0a0b0c0d0e0f"

    async with sn2_mock_bt_client.mock_behavior(
        set_commitment=[None],
    ):
        response = await test_client.post(
            "/api/v1/identity/sn2/subnet/2/commitments",
            json={"commitment": commitment_data},
        )

    assert response.status_code == HTTP_201_CREATED
    assert response.json() == {
        "detail": "Commitment set successfully.",
    }
    assert sn2_mock_bt_client.calls["set_commitment"] == [
        (2, bytes.fromhex(commitment_data[2:])),
    ]


@pytest.mark.asyncio
async def test_set_commitment_identity_blockchain_error(
    test_client: AsyncTestClient, sn1_mock_bt_client: MockBittensorClient, monkeypatch
):
    """
    Test that blockchain errors return 502 Bad Gateway after retries exhausted.
    """
    # Set retry attempts to 0 for faster test
    monkeypatch.setattr("pylon_client.service.tasks.settings.commitment_retry_attempts", 0)

    commitment_data = "0102030405060708"

    async with sn1_mock_bt_client.mock_behavior(
        set_commitment=[RuntimeError("Blockchain connection failed")],
    ):
        response = await test_client.post(
            "/api/v1/identity/sn1/subnet/1/commitments",
            json={"commitment": commitment_data},
        )

    assert response.status_code == HTTP_502_BAD_GATEWAY
    assert response.json() == {
        "status_code": HTTP_502_BAD_GATEWAY,
        "detail": "Failed to set commitment after 1 attempts: Blockchain connection failed",
    }


@pytest.mark.asyncio
async def test_set_commitment_identity_retries_on_failure(
    test_client: AsyncTestClient, sn1_mock_bt_client: MockBittensorClient, monkeypatch
):
    """
    Test that set_commitment retries on transient failures and succeeds when blockchain recovers.
    """
    # Set retry attempts to 2 and minimal delay for faster test
    monkeypatch.setattr("pylon_client.service.tasks.settings.commitment_retry_attempts", 2)
    monkeypatch.setattr("pylon_client.service.tasks.settings.commitment_retry_delay_seconds", 0.01)

    commitment_data = "0102030405060708"

    async with sn1_mock_bt_client.mock_behavior(
        set_commitment=[
            RuntimeError("First failure"),
            RuntimeError("Second failure"),
            None,  # Third attempt succeeds
        ],
    ):
        response = await test_client.post(
            "/api/v1/identity/sn1/subnet/1/commitments",
            json={"commitment": commitment_data},
        )

    assert response.status_code == HTTP_201_CREATED
    assert response.json() == {
        "detail": "Commitment set successfully.",
    }
    # Verify set_commitment was called 3 times (2 failures + 1 success)
    assert len(sn1_mock_bt_client.calls["set_commitment"]) == 3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("invalid_data", "expected_message"),
    [
        pytest.param("not_hex", "Value error, passed commitment data is not a valid hex string.", id="invalid_hex"),
        pytest.param(123, "Value error, commitment must be bytes or hex string", id="invalid_type_int"),
        pytest.param([], "Value error, commitment must be bytes or hex string", id="invalid_type_list"),
        pytest.param(
            "0xGGHH", "Value error, passed commitment data is not a valid hex string.", id="invalid_hex_chars"
        ),
        pytest.param("0xabc", "Value error, passed commitment data is not a valid hex string.", id="odd_length_hex"),
        pytest.param(None, "Value error, commitment must be bytes or hex string", id="none_value"),
        pytest.param("", "Data should have at least 1 byte", id="empty_hex_string"),
        pytest.param("0x", "Data should have at least 1 byte", id="empty_0x_prefix"),
    ],
)
async def test_set_commitment_identity_invalid_data(test_client: AsyncTestClient, invalid_data, expected_message):
    """
    Test setting a commitment with invalid data.
    """
    response = await test_client.post(
        "/api/v1/identity/sn1/subnet/1/commitments",
        json={"commitment": invalid_data},
    )

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json() == {
        "status_code": HTTP_400_BAD_REQUEST,
        "detail": "Validation failed for POST /api/v1/identity/sn1/subnet/1/commitments",
        "extra": [
            {
                "message": expected_message,
                "key": "commitment",
            }
        ],
    }
