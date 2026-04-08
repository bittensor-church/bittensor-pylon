import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_unstable_public_identity_login_returns_identity_metadata(unauthenticated_test_client, snapshot_json):
    response = await unauthenticated_test_client.post("/api/_unstable/login/identity/sn1", json={"token": "token_sn1"})

    assert response.status_code == HTTP_200_OK
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_unstable_public_identity_login_unknown_identity_returns_404(unauthenticated_test_client, snapshot_json):
    response = await unauthenticated_test_client.post(
        "/api/_unstable/login/identity/unknown", json={"token": "whatever"}
    )

    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_unstable_public_identity_login_missing_token_returns_400_or_422(
    unauthenticated_test_client, snapshot_json
):
    response = await unauthenticated_test_client.post("/api/_unstable/login/identity/sn1", json={})

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json() == snapshot_json


@pytest.mark.asyncio
async def test_unstable_public_identity_login_invalid_token_returns_401(unauthenticated_test_client):
    response = await unauthenticated_test_client.post(
        "/api/_unstable/login/identity/sn1", json={"token": "wrong_token"}
    )

    assert response.status_code == HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Invalid token", "status_code": 401}
