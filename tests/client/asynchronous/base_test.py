from abc import ABC, abstractmethod
from http import HTTPMethod

import pytest
from httpx import ConnectTimeout, Response, codes

from pylon_client._internal.client.asynchronous.client import AsyncPylonClient
from pylon_client._internal.common.endpoints import Endpoint
from pylon_client._internal.common.exceptions import (
    PylonClosed,
    PylonMisconfigured,
    PylonRequestException,
    PylonResponseException,
)
from pylon_client._internal.common.responses import PylonResponse
from pylon_client.service.main import app


class BaseEndpointTest(ABC):
    """
    Base class for testing Pylon client endpoints.

    Provides common tests for all endpoints:
    - test_request_error: Verifies PylonRequestException after retries exhausted.
    - test_response_error: Verifies PylonResponseException on server returning error response.
    - test_not_opened: Verifies PylonClosed exception is thrown when client is used without opening it.
    - test_no_credentials: Verifies PylonMisconfigured when credentials are missing in the config.
    - test_retries: Verifies retry mechanism works (2 failures, then success).
    - test_success: Verifies successful response parsing and validation.

    Other tests like data validation or special cases should be implemented by hand.

    Required class attributes to override:
    - endpoint_name: The Endpoint enum value for the route (e.g., Endpoint.NEURONS)
    - route_params: Dict of parameters for route_reverse (e.g., {"netuid": 1, "block_number": 1000})
    - client_fixture_name: Name of the client fixture to use (e.g., "identity_client")
    - no_credentials_error_message: Expected error message when credentials missing

    Optional class attributes:
    - http_method: HTTP method for the endpoint (default: HTTPMethod.GET)

    Required methods to implement:
    - make_endpoint_call: Async method that calls the endpoint via python client. Pylon client should call
        the endpoint mocked, using the URL generated via route_reverse.

    Required fixtures to implement:
    - success_response: Fixture that returns the object expected when the endpoint is successfully called.

    When implementing tests you should probably use one of the subclasses of this class defined below:
    - IdentityEndpointTest
    - OpenAccessEndpointTest
    """

    endpoint: Endpoint
    route_params: dict
    http_method: HTTPMethod = HTTPMethod.GET
    client_fixture_name: str
    no_credentials_error_message: str

    @abstractmethod
    async def make_endpoint_call(self, client: AsyncPylonClient) -> PylonResponse: ...

    @pytest.fixture
    @abstractmethod
    def success_response(self): ...

    @pytest.fixture
    def pylon_client(self, request) -> AsyncPylonClient:
        return request.getfixturevalue(self.client_fixture_name)

    @pytest.fixture
    def endpoint_url(self):
        return app.route_reverse(self.endpoint.reverse, **self.route_params)

    @pytest.fixture
    def route_mock(self, service_mock, endpoint_url):
        mock_method = getattr(service_mock, self.http_method.lower())
        return mock_method(endpoint_url)

    def _setup_login_mock(self, service_mock):
        pass

    def _get_no_credentials_error_message(self) -> str:
        return self.no_credentials_error_message

    @pytest.mark.asyncio
    async def test_request_error(self, route_mock, pylon_client, service_mock):
        self._setup_login_mock(service_mock)
        assert pylon_client.config.retry.stop.max_attempt_number <= 3
        route_mock.mock(side_effect=ConnectTimeout("Connection timed out"))

        async with pylon_client:
            with pytest.raises(PylonRequestException, match="An error occurred while making a request to Pylon API."):
                await self.make_endpoint_call(pylon_client)

    @pytest.mark.asyncio
    async def test_response_error(self, service_mock, pylon_client, route_mock):
        self._setup_login_mock(service_mock)
        route_mock.mock(return_value=Response(status_code=codes.INTERNAL_SERVER_ERROR))

        async with pylon_client:
            with pytest.raises(PylonResponseException, match="Invalid response from Pylon API."):
                await self.make_endpoint_call(pylon_client)

    @pytest.mark.asyncio
    async def test_not_opened(self, pylon_client):
        with pytest.raises(PylonClosed, match="The communicator is closed."):
            await self.make_endpoint_call(pylon_client)

    @pytest.mark.asyncio
    async def test_no_credentials(self, client_no_credentials):
        async with client_no_credentials:
            with pytest.raises(PylonMisconfigured, match=self._get_no_credentials_error_message()):
                await self.make_endpoint_call(client_no_credentials)

    @pytest.mark.asyncio
    async def test_retries(self, service_mock, route_mock, pylon_client, success_response):
        assert pylon_client.config.retry.stop.max_attempt_number == 3
        self._setup_login_mock(service_mock)
        route_mock.mock(
            side_effect=[
                ConnectTimeout("Connection timed out"),
                ConnectTimeout("Connection timed out"),
                Response(status_code=codes.OK, json=success_response.model_dump(mode="json")),
            ]
        )
        async with pylon_client:
            await self.make_endpoint_call(pylon_client)

    @pytest.mark.asyncio
    async def test_success(self, pylon_client, service_mock, route_mock, success_response):
        """
        Test endpoint returns correct response on success.
        """
        self._setup_login_mock(service_mock)

        route_mock.mock(return_value=Response(status_code=codes.OK, json=success_response.model_dump(mode="json")))

        async with pylon_client:
            response = await self.make_endpoint_call(pylon_client)

        assert response == success_response


class IdentityEndpointTest(BaseEndpointTest, ABC):
    """
    Base class for testing identity API endpoints.

    Extends BaseEndpointTest with identity-specific configuration and tests.

    Provides all tests from BaseEndpointTest plus:
    - test_login_request_error: Verifies login request errors are propagated
    - test_login_response_error: Verifies login response errors are propagated

    Pre-configured attributes:
    - client_fixture_name: Set to "identity_client"
    - no_credentials_error_message: Set to identity-specific error message

    Required to override (same as BaseEndpointTest):
    - endpoint_name: The Endpoint enum value
    - route_params: Route parameters including identity_name and netuid
    - make_endpoint_call(client)
    - success_response fixture

    Example:
        class TestIdentityGetNeurons(IdentityEndpointTest):
            endpoint_name = Endpoint.NEURONS
            route_params = {"identity_name": "sn1", "netuid": 1, "block_number": 1000}

            async def make_endpoint_call(self, client):
                return await client.identity.get_neurons(block_number=BlockNumber(1000))

            @pytest.fixture
            def success_response(self, neuron_factory: NeuronFactory) -> GetNeuronsResponse:
                neurons = neuron_factory.batch(2)
                return GetNeuronsResponse(
                    block=Block(number=1000, hash="0x123"),
                    neurons={neuron.hotkey: neuron for neuron in neurons}
                )
    """

    client_fixture_name = "identity_client"
    no_credentials_error_message = "Can not use identity api - no identity name or token provided in config."

    def _setup_login_mock(self, service_mock):
        login_url = app.route_reverse(Endpoint.IDENTITY_LOGIN.reverse, identity_name="sn1")
        service_mock.post(login_url).mock(
            return_value=Response(status_code=codes.OK, json={"netuid": 1, "identity_name": "sn1"})
        )

    @pytest.mark.asyncio
    async def test_login_request_error(self, pylon_client, service_mock):
        assert pylon_client.config.retry.stop.max_attempt_number <= 3
        login_url = app.route_reverse(Endpoint.IDENTITY_LOGIN.reverse, identity_name="sn1")
        service_mock.post(login_url).mock(side_effect=ConnectTimeout("Connection timed out"))

        async with pylon_client:
            with pytest.raises(PylonRequestException, match="An error occurred while making a request to Pylon API."):
                await self.make_endpoint_call(pylon_client)

    @pytest.mark.asyncio
    async def test_login_response_error(self, pylon_client, service_mock):
        login_url = app.route_reverse(Endpoint.IDENTITY_LOGIN.reverse, identity_name="sn1")
        service_mock.post(login_url).mock(return_value=Response(status_code=codes.INTERNAL_SERVER_ERROR))

        async with pylon_client:
            with pytest.raises(PylonResponseException, match="Invalid response from Pylon API."):
                await self.make_endpoint_call(pylon_client)


class OpenAccessEndpointTest(BaseEndpointTest, ABC):
    """
    Base class for testing open access API endpoints.

    Extends BaseEndpointTest with open access-specific configuration.

    Provides all tests from BaseEndpointTest (6 common tests).

    Pre-configured attributes:
    - client_fixture_name: Set to "open_access_client"
    - no_credentials_error_message: Set to open access-specific error message

    Required to override (same as BaseEndpointTest):
    - endpoint_name: The Endpoint enum value
    - route_params: Route parameters including netuid
    - make_endpoint_call(client)
    - success_response fixture

    Example:
        class TestOpenAccessGetNeurons(OpenAccessEndpointTest):
            endpoint_name = Endpoint.NEURONS
            route_params = {"netuid": 1, "block_number": 1000}

            async def make_endpoint_call(self, client):
                return await client.open_access.get_neurons(netuid=NetUid(1), block_number=BlockNumber(1000))

            @pytest.fixture
            def success_response(self, neuron_factory: NeuronFactory) -> GetNeuronsResponse:
                neurons = neuron_factory.batch(2)
                return GetNeuronsResponse(
                    block=Block(number=1000, hash="0x123"),
                    neurons={neuron.hotkey: neuron for neuron in neurons}
                )
    """

    client_fixture_name = "open_access_client"
    no_credentials_error_message = "Can not use open access api - no open access token provided in config."
