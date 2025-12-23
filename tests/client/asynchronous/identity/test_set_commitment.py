import json
from http import HTTPMethod

import pytest
from httpx import Response, codes
from pydantic import ValidationError

from pylon_client._internal.common.endpoints import Endpoint
from pylon_client._internal.common.responses import SetCommitmentResponse
from pylon_client._internal.common.types import CommitmentDataBytes, CommitmentDataHex
from tests.client.asynchronous.base_test import IdentityEndpointTest


class TestAsyncIdentitySetCommitment(IdentityEndpointTest):
    endpoint = Endpoint.COMMITMENTS
    route_params = {"identity_name": "sn1", "netuid": 1}
    http_method = HTTPMethod.POST

    async def make_endpoint_call(self, client):
        return await client.identity.set_commitment(commitment=CommitmentDataBytes(b"\xaa\xbb\xcc\xdd"))

    @pytest.fixture
    def success_response(self) -> SetCommitmentResponse:
        return SetCommitmentResponse()

    @pytest.mark.asyncio
    async def test_success(self, pylon_client, service_mock, route_mock, success_response):
        await super().test_success(pylon_client, service_mock, route_mock, success_response)
        assert json.loads(route_mock.calls.last.request.content) == {"commitment": "0xaabbccdd"}

    @pytest.mark.asyncio
    async def test_success_with_hex_string(self, pylon_client, service_mock, route_mock, success_response):
        self._setup_login_mock(service_mock)
        route_mock.mock(return_value=Response(status_code=codes.OK, json=success_response.model_dump(mode="json")))

        async with pylon_client:
            response = await pylon_client.identity.set_commitment(commitment=CommitmentDataHex("0xAaBbCcDd"))

        assert response == success_response
        assert json.loads(route_mock.calls.last.request.content) == {"commitment": "0xaabbccdd"}

    @pytest.mark.asyncio
    async def test_success_with_hex_without_0x_prefix(self, pylon_client, service_mock, route_mock, success_response):
        """
        Test setting commitment with hex string without 0x prefix.
        """
        self._setup_login_mock(service_mock)
        route_mock.mock(return_value=Response(status_code=codes.OK, json=success_response.model_dump(mode="json")))

        async with pylon_client:
            response = await pylon_client.identity.set_commitment(commitment=CommitmentDataHex("aabbccdd"))

        assert response == success_response
        assert json.loads(route_mock.calls.last.request.content) == {"commitment": "0xaabbccdd"}

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "invalid_commitment,expected_errors",
        [
            pytest.param(
                "not_hex",
                [
                    {
                        "type": "value_error",
                        "loc": ("commitment",),
                        "msg": "Value error, passed commitment data is not a valid hex string.",
                    }
                ],
                id="invalid_hex",
            ),
            pytest.param(
                123,
                [
                    {
                        "type": "value_error",
                        "loc": ("commitment",),
                        "msg": "Value error, commitment must be bytes or hex string",
                    }
                ],
                id="invalid_type",
            ),
            pytest.param(
                "0xGGHH",
                [
                    {
                        "type": "value_error",
                        "loc": ("commitment",),
                        "msg": "Value error, passed commitment data is not a valid hex string.",
                    }
                ],
                id="invalid_hex_chars",
            ),
            pytest.param(
                "0xabc",
                [
                    {
                        "type": "value_error",
                        "loc": ("commitment",),
                        "msg": "Value error, passed commitment data is not a valid hex string.",
                    }
                ],
                id="odd_length_hex",
            ),
            pytest.param(
                None,
                [
                    {
                        "type": "value_error",
                        "loc": ("commitment",),
                        "msg": "Value error, commitment must be bytes or hex string",
                    }
                ],
                id="none_value",
            ),
            pytest.param(
                b"",
                [
                    {
                        "type": "bytes_too_short",
                        "loc": ("commitment",),
                        "msg": "Data should have at least 1 byte",
                    }
                ],
                id="empty_bytes",
            ),
            pytest.param(
                "",
                [
                    {
                        "type": "bytes_too_short",
                        "loc": ("commitment",),
                        "msg": "Data should have at least 1 byte",
                    }
                ],
                id="empty_hex_string",
            ),
            pytest.param(
                "0x",
                [
                    {
                        "type": "bytes_too_short",
                        "loc": ("commitment",),
                        "msg": "Data should have at least 1 byte",
                    }
                ],
                id="empty_0x_prefix",
            ),
        ],
    )
    async def test_client_validation_error(self, pylon_client, service_mock, invalid_commitment, expected_errors):
        """
        Test that client raises ValidationError when using it with invalid commitment data.
        """
        self._setup_login_mock(service_mock)

        async with pylon_client:
            with pytest.raises(ValidationError) as exc_info:
                await pylon_client.identity.set_commitment(commitment=invalid_commitment)

        errors = exc_info.value.errors(include_url=False, include_context=False, include_input=False)
        assert errors == expected_errors
