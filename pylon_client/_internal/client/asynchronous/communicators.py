import logging
from abc import ABC, abstractmethod
from functools import singledispatchmethod
from typing import Generic, TypeVar

from httpx import AsyncClient, HTTPStatusError, Request, RequestError, Response

from pylon_client._internal.client.asynchronous.config import AsyncConfig
from pylon_client._internal.common.endpoints import Endpoint
from pylon_client._internal.common.exceptions import PylonClosed, PylonRequestException, PylonResponseException
from pylon_client._internal.common.requests import (
    AuthenticatedPylonRequest,
    GetCommitmentRequest,
    GetCommitmentsRequest,
    GetLatestNeuronsRequest,
    GetLatestValidatorsRequest,
    GetNeuronsRequest,
    GetOwnCommitmentRequest,
    GetRecentNeuronsRequest,
    GetValidatorsRequest,
    IdentityLoginRequest,
    PylonRequest,
    SetCommitmentRequest,
    SetWeightsRequest,
)
from pylon_client._internal.common.responses import PylonResponse

RawRequestT = TypeVar("RawRequestT")
RawResponseT = TypeVar("RawResponseT")
PylonResponseT = TypeVar("PylonResponseT", bound=PylonResponse)


logger = logging.getLogger(__name__)


class AbstractAsyncCommunicator(Generic[RawRequestT, RawResponseT], ABC):
    """
    Base for every communicator class.

    Communicators are objects that Pylon client uses to communicate with Pylon API. It translates between the client
    interface (Api classes) and the Pylon API interface,
    for example, changing an http response object into a PylonResponse object.
    """

    def __init__(self, config: AsyncConfig):
        self.config = config
        self.is_open = False

    async def __aenter__(self):
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def open(self) -> None:
        """
        Sets the `is_open` attribute to True and calls the open handler specific to the subclass.

        Raises:
            ValueError: When trying to open the already opened communicator.
        """
        if self.is_open:
            raise ValueError("Communicator is already open.")
        self.is_open = True
        await self._open()

    async def close(self) -> None:
        """
        Sets the `is_open` attribute to False and calls the close handler specific to the subclass.

        Raises:
            ValueError: When trying to close the already closed communicator.
        """
        if not self.is_open:
            raise ValueError("Communicator is already closed.")
        self.is_open = False
        await self._close()

    async def request(self, request: PylonRequest[PylonResponseT]) -> PylonResponseT:
        """
        Entrypoint to the Pylon API.

        Makes a request to the Pylon API based on a passed PylonRequest.
        Retries on failures based on a retry config.
        Returns a response translated into a PylonResponse instance.

        Raises:
            PylonClosed: When the communicator is closed while calling this method.
            PylonRequestException: If pylon client fails to communicate with the Pylon server after all retry attempts.
            PylonResponseException: If pylon client receives error response from the Pylon server.
        """
        if not self.is_open:
            raise PylonClosed("The communicator is closed.")
        raw_request = await self._translate_request(request)
        raw_response: RawResponseT | None = None
        async for attempt in self.config.retry.copy():
            with attempt:
                raw_response = await self._request(raw_request)

        assert raw_response is not None
        return await self._translate_response(request, raw_response)

    @abstractmethod
    async def _open(self) -> None:
        """
        Prepares the communicator to work. Sets all the fields necessary for the client to work,
        for example, an http client.
        """

    @abstractmethod
    async def _close(self) -> None:
        """
        Performs any cleanup necessary on the communicator closeup. Cleans up connections etc...
        """

    @abstractmethod
    async def _request(self, request: RawRequestT) -> RawResponseT:
        """
        Makes a raw response out of a raw request by communicating with Pylon.

        Raises:
            PylonRequestError: In case the request fails (no response is received from the server).
        """

    @abstractmethod
    async def _translate_request(self, request: PylonRequest) -> RawRequestT:
        """
        Translates PylonRequest into a raw request object that will be used to communicate with Pylon.
        """

    @abstractmethod
    async def _translate_response(
        self, pylon_request: PylonRequest[PylonResponseT], response: RawResponseT
    ) -> PylonResponseT:
        """
        Translates the outcome of the _request method (raw response object) into a PylonResponse instance.

        Raises:
            PylonResponseError: In case the response is an error response, this exception may be raised.
        """


class AsyncHttpCommunicator(AbstractAsyncCommunicator[Request, Response]):
    """
    Communicates with Pylon API through HTTP.
    """

    def __init__(self, config: AsyncConfig):
        super().__init__(config)
        self._raw_client: AsyncClient | None = None

    async def _open(self) -> None:
        logger.debug(f"Opening communicator for the server {self.config.address}")
        self._raw_client = AsyncClient(base_url=self.config.address)

    async def _close(self) -> None:
        logger.debug(f"Closing communicator for the server {self.config.address}")
        if self._raw_client is not None:
            await self._raw_client.aclose()
        self._raw_client = None

    def _build_url(self, endpoint: Endpoint, request: PylonRequest) -> str:
        if isinstance(request, AuthenticatedPylonRequest):
            return endpoint.absolute_url(
                request.version,
                netuid_=request.netuid,
                identity_name_=request.identity_name,
                **request.model_dump(exclude={"netuid", "identity_name"}),
            )
        return endpoint.absolute_url(request.version, **request.model_dump())

    @singledispatchmethod
    async def _translate_request(self, request: PylonRequest) -> Request:  # type: ignore
        raise NotImplementedError(f"Request of type {type(request).__name__} is not supported.")

    @_translate_request.register
    async def _(self, request: SetWeightsRequest) -> Request:
        assert self._raw_client is not None
        url = self._build_url(Endpoint.SUBNET_WEIGHTS, request)
        return self._raw_client.build_request(
            method=Endpoint.SUBNET_WEIGHTS.method,
            url=url,
            json=request.model_dump(include={"weights"}),
        )

    @_translate_request.register
    async def _(self, request: GetNeuronsRequest) -> Request:
        assert self._raw_client is not None
        url = self._build_url(Endpoint.NEURONS, request)
        return self._raw_client.build_request(method=Endpoint.NEURONS.method, url=url)

    @_translate_request.register
    async def _(self, request: GetLatestNeuronsRequest) -> Request:
        assert self._raw_client is not None
        url = self._build_url(Endpoint.LATEST_NEURONS, request)
        return self._raw_client.build_request(method=Endpoint.LATEST_NEURONS.method, url=url)

    @_translate_request.register
    async def _(self, request: GetRecentNeuronsRequest) -> Request:
        assert self._raw_client is not None
        url = self._build_url(Endpoint.RECENT_NEURONS, request)
        return self._raw_client.build_request(method=Endpoint.RECENT_NEURONS.method, url=url)

    @_translate_request.register
    async def _(self, request: GetValidatorsRequest) -> Request:
        assert self._raw_client is not None
        url = self._build_url(Endpoint.VALIDATORS, request)
        return self._raw_client.build_request(method=Endpoint.VALIDATORS.method, url=url)

    @_translate_request.register
    async def _(self, request: GetLatestValidatorsRequest) -> Request:
        assert self._raw_client is not None
        url = self._build_url(Endpoint.LATEST_VALIDATORS, request)
        return self._raw_client.build_request(method=Endpoint.LATEST_VALIDATORS.method, url=url)

    @_translate_request.register
    async def _(self, request: IdentityLoginRequest) -> Request:
        assert self._raw_client is not None
        url = self._build_url(Endpoint.IDENTITY_LOGIN, request)
        return self._raw_client.build_request(method=Endpoint.IDENTITY_LOGIN.method, url=url, json=request.model_dump())

    @_translate_request.register
    async def _(self, request: GetCommitmentsRequest) -> Request:
        assert self._raw_client is not None
        url = self._build_url(Endpoint.LATEST_COMMITMENTS, request)
        return self._raw_client.build_request(method=Endpoint.LATEST_COMMITMENTS.method, url=url)

    @_translate_request.register
    async def _(self, request: GetCommitmentRequest) -> Request:
        assert self._raw_client is not None
        url = self._build_url(Endpoint.LATEST_COMMITMENTS_HOTKEY, request)
        return self._raw_client.build_request(method=Endpoint.LATEST_COMMITMENTS_HOTKEY.method, url=url)

    @_translate_request.register
    async def _(self, request: GetOwnCommitmentRequest) -> Request:
        assert self._raw_client is not None
        url = self._build_url(Endpoint.LATEST_COMMITMENTS_SELF, request)
        return self._raw_client.build_request(method=Endpoint.LATEST_COMMITMENTS_SELF.method, url=url)

    @_translate_request.register
    async def _(self, request: SetCommitmentRequest) -> Request:
        assert self._raw_client is not None
        url = self._build_url(Endpoint.COMMITMENTS, request)
        return self._raw_client.build_request(
            method=Endpoint.COMMITMENTS.method,
            url=url,
            json=request.model_dump(include={"commitment"}),
        )

    async def _translate_response(
        self, pylon_request: PylonRequest[PylonResponseT], response: Response
    ) -> PylonResponseT:
        return pylon_request.response_cls(**response.json())

    async def _request(self, request: Request) -> Response:
        assert self._raw_client and not self._raw_client.is_closed, (
            "Communicator is not open, use context manager or open() method before making a request."
        )
        try:
            logger.debug(f"Performing request to {request.url}")
            response = await self._raw_client.send(request)
        except RequestError as e:
            return await self._handle_request_error(e)
        try:
            response.raise_for_status()
        except HTTPStatusError as e:
            return await self._handle_status_error(e)
        return response

    async def _handle_request_error(self, exc: RequestError) -> Response:
        raise PylonRequestException("An error occurred while making a request to Pylon API.") from exc

    # TODO: Add more info about error response to the exception.
    async def _handle_status_error(self, exc: HTTPStatusError) -> Response:
        raise PylonResponseException("Invalid response from Pylon API.") from exc
