import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_v1_public_identity_login_returns_identity_metadata(unauthenticated_test_client, snapshot_json):
    response = await unauthenticated_test_client.post("/api/v1/login/identity/sn1", json={"token": "token_sn1"})

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_v1_public_identity_login_unknown_identity_returns_404(unauthenticated_test_client, snapshot_json):
    response = await unauthenticated_test_client.post("/api/v1/login/identity/unknown", json={"token": "whatever"})

    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_v1_public_identity_login_missing_token_returns_400_or_422(unauthenticated_test_client, snapshot_json):
    response = await unauthenticated_test_client.post("/api/v1/login/identity/sn1", json={})

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_v1_public_identity_login_invalid_token_returns_401(unauthenticated_test_client):
    response = await unauthenticated_test_client.post("/api/v1/login/identity/sn1", json={"token": "wrong_token"})

    assert response.status_code == HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Invalid token", "status_code": 401}


@pytest.mark.asyncio
async def test_v1_public_identity_login_sets_session_cookie(unauthenticated_test_client):
    response = await unauthenticated_test_client.post("/api/v1/login/identity/sn1", json={"token": "token_sn1"})

    assert response.status_code == HTTP_200_OK
    assert "session" in response.cookies


@pytest.mark.asyncio
async def test_v1_public_identity_login_preserves_multiple_identity_sessions(unauthenticated_test_client):
    await unauthenticated_test_client.post("/api/v1/login/identity/sn1", json={"token": "token_sn1"})
    await unauthenticated_test_client.post("/api/v1/login/identity/sn2", json={"token": "token_sn2"})

    response_sn1 = await unauthenticated_test_client.get("/api/v1/identity/sn1/subnet/1/block/latest/neurons")
    response_sn2 = await unauthenticated_test_client.get("/api/v1/identity/sn2/subnet/2/block/latest/neurons")

    assert response_sn1.status_code == HTTP_200_OK
    assert response_sn2.status_code == HTTP_200_OK
