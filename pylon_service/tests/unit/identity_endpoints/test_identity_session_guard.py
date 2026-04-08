import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_identity_endpoint_without_session_returns_401(unauthenticated_test_client):
    response = await unauthenticated_test_client.get("/api/v1/identity/sn1/subnet/1/block/latest/neurons")

    assert response.status_code == HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated", "status_code": 401}


@pytest.mark.asyncio
async def test_identity_endpoint_with_different_identity_session_returns_401(unauthenticated_test_client):
    await unauthenticated_test_client.post("/api/v1/login/identity/sn2", json={"token": "token_sn2"})

    response = await unauthenticated_test_client.get("/api/v1/identity/sn1/subnet/1/block/latest/neurons")

    assert response.status_code == HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated", "status_code": 401}


@pytest.mark.asyncio
async def test_identity_endpoint_with_correct_identity_but_wrong_netuid_returns_403(unauthenticated_test_client):
    await unauthenticated_test_client.post("/api/v1/login/identity/sn1", json={"token": "token_sn1"})

    response = await unauthenticated_test_client.get("/api/v1/identity/sn1/subnet/99/block/latest/neurons")

    assert response.status_code == HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "Session netuid does not match requested netuid", "status_code": 403}


@pytest.mark.asyncio
async def test_identity_endpoint_with_valid_session_succeeds(unauthenticated_test_client):
    await unauthenticated_test_client.post("/api/v1/login/identity/sn1", json={"token": "token_sn1"})

    response = await unauthenticated_test_client.get("/api/v1/identity/sn1/subnet/1/block/latest/neurons")

    assert response.status_code == HTTP_200_OK


@pytest.mark.asyncio
async def test_unstable_identity_endpoint_without_session_returns_401(unauthenticated_test_client):
    response = await unauthenticated_test_client.get("/api/_unstable/identity/sn1/subnet/1/block/latest/neurons")

    assert response.status_code == HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated", "status_code": 401}
