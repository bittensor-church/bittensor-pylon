import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from functools import partial
from typing import Generic, NewType, TypeVar

from pylon._internal.client.communicators.abstract import AbstractCommunicator
from pylon._internal.common.exceptions import PylonClosed, PylonForbidden, PylonUnauthorized
from pylon._internal.common.requests import GetLatestNeuronsRequest, GetNeuronsRequest, PylonRequest, SetWeightsRequest
from pylon._internal.common.responses import GetNeuronsResponse, LoginResponse, PylonResponse, SetWeightsResponse
from pylon._internal.common.types import BlockNumber, Hotkey, NetUid, Weight

ResponseT = TypeVar("ResponseT", bound=PylonResponse)
LoginResponseT = TypeVar("LoginResponseT", bound=LoginResponse)

LoginGeneration = NewType("LoginGeneration", int)


class AbstractAsyncApi(Generic[LoginResponseT], ABC):
    """
    Class that represents the API available in the service.
    It provides the set of methods to query the service endpoints in a simple way.
    The class takes care of authentication and re-authentication.
    """

    def __init__(self, communicator: AbstractCommunicator):
        self._communicator = communicator
        self._login_response: LoginResponseT | None = None
        self._login_lock = asyncio.Lock()
        self._login_generation: LoginGeneration = LoginGeneration(0)

    @abstractmethod
    async def _login(self) -> LoginResponseT:
        """
        This method should call the login endpoint and return the proper LoginResponse subclass instance, so that
        the other methods may use the data returned from the login endpoint.
        """

    async def _send_request(self, request: PylonRequest[ResponseT]) -> ResponseT:
        """
        Sends the request via the communicator, first checking if the communicator is open.

        Raises:
            PylonClosed: When the communicator is closed while calling this method.
        """
        if not self._communicator.is_open:
            raise PylonClosed("The communicator is closed.")
        return await self._communicator.request(request)

    async def _authenticated_request(
        self,
        request_factory: Callable[[], Awaitable[PylonRequest[ResponseT]]],
        stale_generation: LoginGeneration = LoginGeneration(-1),
    ) -> tuple[PylonRequest[ResponseT], LoginGeneration]:
        """
        Makes the PylonRequest instance by calling the factory method, first making sure that the login data is
        available for the factory method to prepare the request.
        """
        async with self._login_lock:
            if self._login_response is None or stale_generation == self._login_generation:
                self._login_response = await self._login()
                self._login_generation = LoginGeneration(self._login_generation + 1)
            return await request_factory(), self._login_generation

    async def _send_authenticated_request(
        self, request_factory: Callable[[], Awaitable[PylonRequest[ResponseT]]]
    ) -> ResponseT:
        """
        Performs the request, first authenticating if needed.
        Re-authenticates if Pylon returns Unauthorized or Forbidden errors for the cases like session expiration
        or server restarted with different configuration.
        """
        request, login_generation = await self._authenticated_request(request_factory)
        try:
            return await self._send_request(request)
        except (PylonUnauthorized, PylonForbidden):
            # Retry the request after generating new login data. Login will not be performed if reauthentication was
            # performed by another task.
            request, _ = await self._authenticated_request(request_factory, stale_generation=login_generation)
            return await self._send_request(request)


class AbstractOpenAccessAsyncApi(AbstractAsyncApi[LoginResponseT], ABC):
    """
    Interface of the open access API.
    """

    @abstractmethod
    async def _get_neurons_request(self, netuid: NetUid, block_number: BlockNumber) -> GetNeuronsRequest: ...

    @abstractmethod
    async def _get_latest_neurons_request(self, netuid: NetUid) -> GetLatestNeuronsRequest: ...

    # Public API

    async def get_neurons(self, netuid: NetUid, block_number: BlockNumber) -> GetNeuronsResponse:
        return await self._send_authenticated_request(partial(self._get_neurons_request, netuid, block_number))

    async def get_latest_neurons(self, netuid: NetUid) -> GetNeuronsResponse:
        return await self._send_authenticated_request(partial(self._get_latest_neurons_request, netuid))


class AbstractIdentityAsyncApi(AbstractAsyncApi[LoginResponseT], ABC):
    """
    Interface of the identity API.
    """

    @abstractmethod
    async def _get_neurons_request(self, block_number: BlockNumber) -> GetNeuronsRequest: ...

    @abstractmethod
    async def _get_latest_neurons_request(self) -> GetLatestNeuronsRequest: ...

    @abstractmethod
    async def _put_weights_request(self, weights: dict[Hotkey, Weight]) -> SetWeightsRequest: ...

    # Public API

    async def get_neurons(self, block_number: BlockNumber) -> GetNeuronsResponse:
        return await self._send_authenticated_request(partial(self._get_neurons_request, block_number))

    async def get_latest_neurons(self) -> GetNeuronsResponse:
        return await self._send_authenticated_request(self._get_latest_neurons_request)

    async def put_weights(self, weights: dict[Hotkey, Weight]) -> SetWeightsResponse:
        return await self._send_authenticated_request(partial(self._put_weights_request, weights))
