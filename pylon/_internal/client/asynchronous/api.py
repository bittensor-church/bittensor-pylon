import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from functools import partial
from typing import Generic, NewType, TypeVar

from pylon._internal.client.asynchronous.communicators import AbstractAsyncCommunicator
from pylon._internal.common.exceptions import PylonClosed, PylonForbidden, PylonMisconfigured, PylonUnauthorized
from pylon._internal.common.requests import (
    GetLatestNeuronsRequest,
    GetNeuronsRequest,
    IdentityLoginRequest,
    PylonRequest,
    SetWeightsRequest,
)
from pylon._internal.common.responses import (
    GetNeuronsResponse,
    IdentityLoginResponse,
    LoginResponse,
    OpenAccessLoginResponse,
    PylonResponse,
    SetWeightsResponse,
)
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

    def __init__(self, communicator: AbstractAsyncCommunicator):
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


class AbstractAsyncOpenAccessApi(AbstractAsyncApi[LoginResponseT], ABC):
    """
    Open access API for querying Bittensor subnet data via Pylon service without identity authentication.

    This API provides read-only access to the chain data across any subnet.
    Requests require an open access token configured in the client.
    The API handles authentication to Pylon service automatically and caches credentials for subsequent requests.

    All methods in this API may raise the following exceptions:
        PylonClosed: When the api method is called and the communicator is closed.
        PylonRequestException: When a network or connection error occurs and all retires are exhausted.
            Requests are retried automatically according to the retry configuration.
        PylonResponseException: When the server returns an error response.
        PylonMisconfigured: When the open access token is not configured.
    """

    # Public API

    async def get_neurons(self, netuid: NetUid, block_number: BlockNumber) -> GetNeuronsResponse:
        """
        Retrieves neurons for a specific subnet at a given block number.

        Args:
            netuid: The unique identifier of the subnet.
            block_number: The blockchain block number to query neurons at.

        Returns:
            GetNeuronsResponse: containing the block information and a dictionary mapping hotkeys to Neuron objects.
        """
        return await self._send_authenticated_request(partial(self._get_neurons_request, netuid, block_number))

    async def get_latest_neurons(self, netuid: NetUid) -> GetNeuronsResponse:
        """
        Retrieves neurons for a specific subnet at the latest available block.

        Args:
            netuid: The unique identifier of the subnet.

        Returns:
            GetNeuronsResponse: containing the latest block information and a dictionary mapping hotkeys to
            Neuron objects.
        """
        return await self._send_authenticated_request(partial(self._get_latest_neurons_request, netuid))

    # Private API

    @abstractmethod
    async def _get_neurons_request(self, netuid: NetUid, block_number: BlockNumber) -> GetNeuronsRequest: ...

    @abstractmethod
    async def _get_latest_neurons_request(self, netuid: NetUid) -> GetLatestNeuronsRequest: ...


class AbstractAsyncIdentityApi(AbstractAsyncApi[LoginResponseT], ABC):
    """
    Identity-authenticated API for subnet-specific operations.

    This API provides access to read and write operations for a specific subnet associated with
    the configured identity. The subnet is determined automatically from the identity credentials.
    Authentication is performed on the first request and cached for subsequent requests.
    The API automatically re-authenticates when sessions expire or authentication errors occur.

    All methods in this API may raise the following exceptions:
        PylonClosed: When the api method is called and the communicator is closed.
        PylonRequestException: When a network or connection error occurs and all retires are exhausted.
            Requests are retried automatically according to the retry configuration.
        PylonResponseException: When the server returns an error response.
        PylonUnauthorized: When authentication fails by the reason of wrong credentials.
        PylonMisconfigured: When required identity credentials (identity_name and identity_token)
            are not configured.
    """

    # Public API

    async def get_neurons(self, block_number: BlockNumber) -> GetNeuronsResponse:
        """
        Retrieves neurons for the authenticated identity's subnet at a given block number.

        Args:
            block_number: The blockchain block number to query neurons at.

        Returns:
            GetNeuronsResponse containing the block information and a dictionary mapping hotkeys to Neuron objects.
        """
        return await self._send_authenticated_request(partial(self._get_neurons_request, block_number))

    async def get_latest_neurons(self) -> GetNeuronsResponse:
        """
        Retrieves neurons for the authenticated identity's subnet at the latest available block.

        Returns:
            GetNeuronsResponse containing the latest block information and a dictionary mapping hotkeys to
            Neuron objects.
        """
        return await self._send_authenticated_request(self._get_latest_neurons_request)

    async def put_weights(self, weights: dict[Hotkey, Weight]) -> SetWeightsResponse:
        """
        Submits weights for neurons in the authenticated identity's subnet.

        Weights are applied asynchronously by the Pylon service. The method returns immediately after
        scheduling the weight update, without waiting for blockchain confirmation. The service handles
        commit-reveal or direct weight setting based on subnet hyperparameters.

        Args:
            weights: Dictionary mapping neuron hotkeys to their respective weight values. Weights should
                be normalized (sum to 1.0) and only include neurons that should receive non-zero weights.

        Returns:
            SetWeightsResponse indicating the weights update has been scheduled.
        """
        return await self._send_authenticated_request(partial(self._put_weights_request, weights))

    # Private API

    @abstractmethod
    async def _get_neurons_request(self, block_number: BlockNumber) -> GetNeuronsRequest: ...

    @abstractmethod
    async def _get_latest_neurons_request(self) -> GetLatestNeuronsRequest: ...

    @abstractmethod
    async def _put_weights_request(self, weights: dict[Hotkey, Weight]) -> SetWeightsRequest: ...


class AsyncOpenAccessApi(AbstractAsyncOpenAccessApi[OpenAccessLoginResponse]):
    async def _login(self) -> OpenAccessLoginResponse:
        if self._communicator.config.open_access_token is None:
            raise PylonMisconfigured("Can not use open access api - no open access token provided in config.")
        # TODO: As part of BACT-168, when authentication is implemented,
        #  make a real request to obtain the session cookie.
        return OpenAccessLoginResponse()

    async def _get_neurons_request(self, netuid: NetUid, block_number: BlockNumber) -> GetNeuronsRequest:
        return GetNeuronsRequest(
            netuid=netuid,
            block_number=block_number,
        )

    async def _get_latest_neurons_request(self, netuid: NetUid) -> GetLatestNeuronsRequest:
        return GetLatestNeuronsRequest(netuid=netuid)


class AsyncIdentityApi(AbstractAsyncIdentityApi[IdentityLoginResponse]):
    async def _login(self) -> IdentityLoginResponse:
        if not self._communicator.config.identity_name or not self._communicator.config.identity_token:
            raise PylonMisconfigured("Can not use identity api - no identity name or token provided in config.")
        return await self._send_request(
            IdentityLoginRequest(
                token=self._communicator.config.identity_token, identity_name=self._communicator.config.identity_name
            )
        )

    async def _get_neurons_request(self, block_number: BlockNumber) -> GetNeuronsRequest:
        assert self._login_response, "Attempted api request without authentication."
        return GetNeuronsRequest(
            netuid=self._login_response.netuid,
            identity_name=self._login_response.identity_name,
            block_number=block_number,
        )

    async def _get_latest_neurons_request(self) -> GetLatestNeuronsRequest:
        assert self._login_response, "Attempted api request without authentication."
        return GetLatestNeuronsRequest(
            netuid=self._login_response.netuid,
            identity_name=self._login_response.identity_name,
        )

    async def _put_weights_request(self, weights: dict[Hotkey, Weight]) -> SetWeightsRequest:
        assert self._login_response, "Attempted api request without authentication."
        return SetWeightsRequest(
            netuid=self._login_response.netuid,
            identity_name=self._login_response.identity_name,
            weights=weights,
        )
