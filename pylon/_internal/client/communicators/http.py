import logging
from functools import singledispatchmethod
from typing import TypeVar

from httpx import AsyncClient, HTTPStatusError, Request, RequestError, Response

from pylon._internal.client.communicators.abstract import AbstractCommunicator
from pylon._internal.client.config import AsyncConfig
from pylon._internal.common.endpoints import Endpoint
from pylon._internal.common.exceptions import PylonRequestException, PylonResponseException
from pylon._internal.common.requests import (
    AuthenticatedPylonRequest,
    GetLatestNeuronsRequest,
    GetNeuronsRequest,
    IdentityLoginRequest,
    PylonRequest,
    SetWeightsRequest,
)
from pylon._internal.common.responses import PylonResponse

logger = logging.getLogger(__name__)


PylonResponseT = TypeVar("PylonResponseT", bound=PylonResponse)


class AsyncHttpCommunicator(AbstractCommunicator[Request, Response]):
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
    async def _(self, request: IdentityLoginRequest) -> Request:
        assert self._raw_client is not None
        url = self._build_url(Endpoint.IDENTITY_LOGIN, request)
        return self._raw_client.build_request(method=Endpoint.IDENTITY_LOGIN.method, url=url, json=request.model_dump())

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
