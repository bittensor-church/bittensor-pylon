from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pylon._internal.client.config import AsyncConfig
from pylon._internal.common.exceptions import PylonClosed
from pylon._internal.common.requests import PylonRequest
from pylon._internal.common.responses import PylonResponse

RawRequestT = TypeVar("RawRequestT")
RawResponseT = TypeVar("RawResponseT")
PylonResponseT = TypeVar("PylonResponseT", bound=PylonResponse)


class AbstractCommunicator(Generic[RawRequestT, RawResponseT], ABC):
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
