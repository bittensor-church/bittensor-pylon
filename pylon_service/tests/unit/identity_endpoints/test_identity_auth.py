"""
Tests for identity endpoint authentication (Bearer token guard and netuid mismatch redirect).
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_308_PERMANENT_REDIRECT, HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN
from litestar.testing import AsyncTestClient


@pytest.mark.asyncio
async def test_no_auth_header_returns_401(test_client: AsyncTestClient):
    response = await test_client.get("/api/v1/identity/sn1/subnet/1/block/latest/neurons")

    assert response.status_code == HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_invalid_auth_format_returns_401(test_client: AsyncTestClient):
    response = await test_client.get(
        "/api/v1/identity/sn1/subnet/1/block/latest/neurons",
        headers={"Authorization": "Basic dXNlcjpwYXNz"},
    )

    assert response.status_code == HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_wrong_token_returns_403(test_client: AsyncTestClient):
    response = await test_client.get(
        "/api/v1/identity/sn1/subnet/1/block/latest/neurons",
        headers={"Authorization": "Bearer wrong_token"},
    )

    assert response.status_code == HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_correct_token_succeeds(test_client: AsyncTestClient):
    response = await test_client.get(
        "/api/v1/identity/sn1/subnet/1/block/latest/neurons",
        headers={"Authorization": "Bearer sn1_token"},
    )

    assert response.status_code == HTTP_200_OK


@pytest.mark.asyncio
async def test_netuid_mismatch_returns_308(test_client: AsyncTestClient):
    response = await test_client.get(
        "/api/v1/identity/sn1/subnet/99/block/latest/neurons",
        headers={"Authorization": "Bearer sn1_token"},
        follow_redirects=False,
    )

    assert response.status_code == HTTP_308_PERMANENT_REDIRECT
    assert response.headers["location"] == "/api/v1/identity/sn1/subnet/1/block/latest/neurons"


@pytest.mark.asyncio
async def test_netuid_mismatch_returns_308_unstable(test_client: AsyncTestClient):
    response = await test_client.get(
        "/api/_unstable/identity/sn1/subnet/99/block/latest/neurons",
        headers={"Authorization": "Bearer sn1_token"},
        follow_redirects=False,
    )

    assert response.status_code == HTTP_308_PERMANENT_REDIRECT
    assert response.headers["location"] == "/api/_unstable/identity/sn1/subnet/1/block/latest/neurons"


@pytest.mark.asyncio
async def test_no_auth_header_returns_401_unstable(test_client: AsyncTestClient):
    response = await test_client.get("/api/_unstable/identity/sn1/subnet/1/block/latest/neurons")

    assert response.status_code == HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_wrong_token_returns_403_unstable(test_client: AsyncTestClient):
    response = await test_client.get(
        "/api/_unstable/identity/sn1/subnet/1/block/latest/neurons",
        headers={"Authorization": "Bearer wrong_token"},
    )

    assert response.status_code == HTTP_403_FORBIDDEN
