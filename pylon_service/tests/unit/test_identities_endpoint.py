"""
Tests for the GET /identities endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK
from litestar.testing import AsyncTestClient

_EXPECTED_RESPONSE = {
    "identities": {
        "sn1": 1,
        "sn1c": 1,
        "sn2": 2,
        "sn3": 3,
        "sn4": 4,
        "sn11": 11,
        "sn21": 21,
        "sn22": 22,
        "sn23": 23,
        "sn24": 24,
        "sn25": 25,
        "sn29": 29,
        "sn30": 30,
    },
}


@pytest.mark.asyncio
async def test_get_identities_v1(test_client: AsyncTestClient):
    response = await test_client.get("/api/v1/identities")

    assert response.status_code == HTTP_200_OK
    assert response.json() == _EXPECTED_RESPONSE


@pytest.mark.asyncio
async def test_get_identities_unstable(open_access_test_client: AsyncTestClient):
    response = await open_access_test_client.get("/api/_unstable/identities")

    assert response.status_code == HTTP_200_OK
    assert response.json() == _EXPECTED_RESPONSE
