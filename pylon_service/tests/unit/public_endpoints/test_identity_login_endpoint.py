import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_v1_public_identity_login_returns_identity_metadata(test_client, snapshot_json):
    response = await test_client.post("/api/v1/login/identity/sn1", json={"token": "token_sn1"})

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_v1_public_identity_login_unknown_identity_returns_404(test_client, snapshot_json):
    response = await test_client.post("/api/v1/login/identity/unknown", json={"token": "whatever"})

    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_v1_public_identity_login_missing_token_returns_400_or_422(test_client, snapshot_json):
    response = await test_client.post("/api/v1/login/identity/sn1", json={})

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json() == snapshot_json
