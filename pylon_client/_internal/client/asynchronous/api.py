import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from functools import partial
from typing import Generic, NewType, TypeVar, cast

from pylon_client._internal.client.asynchronous.communicators import AbstractAsyncCommunicator
from pylon_client._internal.common.exceptions import PylonClosed, PylonForbidden, PylonMisconfigured, PylonUnauthorized
from pylon_client._internal.common.requests import (
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
from pylon_client._internal.common.responses import (
    GetCommitmentResponse,
    GetCommitmentsResponse,
    GetNeuronsResponse,
    GetValidatorsResponse,
    IdentityLoginResponse,
    LoginResponse,
    OpenAccessLoginResponse,
    PylonResponse,
    SetCommitmentResponse,
    SetWeightsResponse,
)
from pylon_client._internal.common.types import (
    BlockNumber,
    CommitmentDataBytes,
    CommitmentDataHex,
    Hotkey,
    NetUid,
    Weight,
)

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

    async def get_recent_neurons(self, netuid: NetUid) -> GetNeuronsResponse:
        """
        Retrieves recent neurons for a specific subnet.

        This method returns neurons from the Pylon service's cache, which might be behind
        the latest block. But it guarantees to provide data no older than configured
        `PYLON_RECENT_OBJECTS_HARD_LIMIT_BLOCKS` blocks with a fast response time.

        Args:
            netuid: The unique identifier of the subnet.

        Returns:
            GetNeuronsResponse: containing cached neuron information and a dictionary mapping hotkeys to
            Neuron objects.

        Raises:
            PylonResponseException:
                - The Pylon service cache doesn't have fresh enough data.
                - The requested subnet is not of one of the configured identities or is not configured
                  for caching recent data via `PYLON_RECENT_OBJECTS_NETUIDS` config variable.
        """
        return await self._send_authenticated_request(partial(self._get_recent_neurons_request, netuid))

    async def get_commitments(self, netuid: NetUid) -> GetCommitmentsResponse:
        """
        Retrieves all commitments for a specific subnet at the latest available block.

        Args:
            netuid: The unique identifier of the subnet.

        Returns:
            GetCommitmentsResponse: containing commitments data mapping hotkeys to commitment data.
        """
        return await self._send_authenticated_request(partial(self._get_commitments_request, netuid))

    async def get_commitment(self, netuid: NetUid, hotkey: Hotkey) -> GetCommitmentResponse:
        """
        Retrieves a specific commitment for a hotkey in a subnet at the latest available block.

        Args:
            netuid: The unique identifier of the subnet.
            hotkey: The hotkey to retrieve the commitment for.

        Returns:
            GetCommitmentResponse: containing the hotkey and its commitment data (None if not found).
        """
        return await self._send_authenticated_request(partial(self._get_commitment_request, netuid, hotkey))

    async def get_validators(self, netuid: NetUid, block_number: BlockNumber) -> GetValidatorsResponse:
        """
        Retrieves validators for a specific subnet at a given block number.

        Validators are neurons with validator_permit=True, sorted by total stake in descending order.

        Args:
            netuid: The unique identifier of the subnet.
            block_number: The blockchain block number to query validators at.

        Returns:
            GetValidatorsResponse: containing the block information and a list of validator Neuron objects.
        """
        return await self._send_authenticated_request(partial(self._get_validators_request, netuid, block_number))

    async def get_latest_validators(self, netuid: NetUid) -> GetValidatorsResponse:
        """
        Retrieves validators for a specific subnet at the latest available block.

        Validators are neurons with validator_permit=True, sorted by total stake in descending order.

        Args:
            netuid: The unique identifier of the subnet.

        Returns:
            GetValidatorsResponse: containing the latest block information and a list of validator Neuron objects.
        """
        return await self._send_authenticated_request(partial(self._get_latest_validators_request, netuid))

    # Private API

    @abstractmethod
    async def _get_neurons_request(self, netuid: NetUid, block_number: BlockNumber) -> GetNeuronsRequest: ...

    @abstractmethod
    async def _get_latest_neurons_request(self, netuid: NetUid) -> GetLatestNeuronsRequest: ...

    @abstractmethod
    async def _get_recent_neurons_request(self, netuid: NetUid) -> GetRecentNeuronsRequest: ...

    @abstractmethod
    async def _get_validators_request(self, netuid: NetUid, block_number: BlockNumber) -> GetValidatorsRequest: ...

    @abstractmethod
    async def _get_latest_validators_request(self, netuid: NetUid) -> GetLatestValidatorsRequest: ...

    @abstractmethod
    async def _get_commitments_request(self, netuid: NetUid) -> GetCommitmentsRequest: ...

    @abstractmethod
    async def _get_commitment_request(self, netuid: NetUid, hotkey: Hotkey) -> GetCommitmentRequest: ...


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

    async def get_recent_neurons(self) -> GetNeuronsResponse:
        """
        Retrieves recent neurons for the authenticated identity's subnet.

        This method returns neurons from the Pylon service's cache, which might be behind
        the latest block. But it guarantees to provide data no older than configured
        `PYLON_RECENT_OBJECTS_HARD_LIMIT_BLOCKS` blocks with a fast response time.

        Returns:
            GetNeuronsResponse: containing cached neuron information and a dictionary mapping hotkeys to
            Neuron objects.

        Raises:
            PylonResponseException: When the Pylon service cache doesn't have fresh enough data.
        """
        return await self._send_authenticated_request(self._get_recent_neurons_request)

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

    async def get_commitments(self) -> GetCommitmentsResponse:
        """
        Retrieves all commitments for the authenticated identity's subnet at the latest available block.

        Returns:
            GetCommitmentsResponse: containing commitments data mapping hotkeys to commitment data.
        """
        return await self._send_authenticated_request(self._get_commitments_request)

    async def get_commitment(self, hotkey: Hotkey) -> GetCommitmentResponse:
        """
        Retrieves a specific commitment for a hotkey in the authenticated identity's subnet.

        Args:
            hotkey: The hotkey to retrieve the commitment for.

        Returns:
            GetCommitmentResponse: containing the hotkey and its commitment data (None if not found).
        """
        return await self._send_authenticated_request(partial(self._get_commitment_request, hotkey))

    async def get_own_commitment(self) -> GetCommitmentResponse:
        """
        Retrieves the commitment for the authenticated identity's own wallet hotkey.

        Returns:
            GetCommitmentResponse: containing the hotkey and its commitment data.
        """
        return await self._send_authenticated_request(self._get_own_commitment_request)

    async def set_commitment(self, commitment: CommitmentDataBytes | CommitmentDataHex) -> SetCommitmentResponse:
        """
        Sets a commitment (model metadata) on-chain for the authenticated identity's wallet hotkey.

        The commitment is applied asynchronously by the Pylon service. The method returns immediately after
        scheduling the commitment update, without waiting for blockchain confirmation.

        Args:
            commitment: The commitment data to set. Can be bytes or hex string format (with or without 0x prefix).

        Returns:
            SetCommitmentResponse indicating the commitment has been set successfully.
        """
        return await self._send_authenticated_request(partial(self._set_commitment_request, commitment))

    async def get_validators(self, block_number: BlockNumber) -> GetValidatorsResponse:
        """
        Retrieves validators for the authenticated identity's subnet at a given block number.

        Validators are neurons with validator_permit=True, sorted by total stake in descending order.

        Args:
            block_number: The blockchain block number to query validators at.

        Returns:
            GetValidatorsResponse: containing the block information and a list of validator Neuron objects.
        """
        return await self._send_authenticated_request(partial(self._get_validators_request, block_number))

    async def get_latest_validators(self) -> GetValidatorsResponse:
        """
        Retrieves validators for the authenticated identity's subnet at the latest available block.

        Validators are neurons with validator_permit=True, sorted by total stake in descending order.

        Returns:
            GetValidatorsResponse: containing the latest block information and a list of validator Neuron objects.
        """
        return await self._send_authenticated_request(self._get_latest_validators_request)

    # Private API

    @abstractmethod
    async def _get_neurons_request(self, block_number: BlockNumber) -> GetNeuronsRequest: ...

    @abstractmethod
    async def _get_latest_neurons_request(self) -> GetLatestNeuronsRequest: ...

    @abstractmethod
    async def _get_recent_neurons_request(self) -> GetRecentNeuronsRequest: ...

    @abstractmethod
    async def _put_weights_request(self, weights: dict[Hotkey, Weight]) -> SetWeightsRequest: ...

    @abstractmethod
    async def _get_commitments_request(self) -> GetCommitmentsRequest: ...

    @abstractmethod
    async def _get_commitment_request(self, hotkey: Hotkey) -> GetCommitmentRequest: ...

    @abstractmethod
    async def _get_own_commitment_request(self) -> GetOwnCommitmentRequest: ...

    @abstractmethod
    async def _set_commitment_request(
        self, commitment: CommitmentDataBytes | CommitmentDataHex
    ) -> SetCommitmentRequest: ...

    @abstractmethod
    async def _get_validators_request(self, block_number: BlockNumber) -> GetValidatorsRequest: ...

    @abstractmethod
    async def _get_latest_validators_request(self) -> GetLatestValidatorsRequest: ...


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

    async def _get_recent_neurons_request(self, netuid: NetUid) -> GetRecentNeuronsRequest:
        return GetRecentNeuronsRequest(netuid=netuid)

    async def _get_commitments_request(self, netuid: NetUid) -> GetCommitmentsRequest:
        return GetCommitmentsRequest(netuid=netuid)

    async def _get_commitment_request(self, netuid: NetUid, hotkey: Hotkey) -> GetCommitmentRequest:
        return GetCommitmentRequest(netuid=netuid, hotkey=hotkey)

    async def _get_validators_request(self, netuid: NetUid, block_number: BlockNumber) -> GetValidatorsRequest:
        return GetValidatorsRequest(netuid=netuid, block_number=block_number)

    async def _get_latest_validators_request(self, netuid: NetUid) -> GetLatestValidatorsRequest:
        return GetLatestValidatorsRequest(netuid=netuid)


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

    async def _get_recent_neurons_request(self) -> GetRecentNeuronsRequest:
        assert self._login_response, "Attempted api request without authentication."
        return GetRecentNeuronsRequest(
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

    async def _get_commitments_request(self) -> GetCommitmentsRequest:
        assert self._login_response, "Attempted api request without authentication."
        return GetCommitmentsRequest(
            netuid=self._login_response.netuid,
            identity_name=self._login_response.identity_name,
        )

    async def _get_commitment_request(self, hotkey: Hotkey) -> GetCommitmentRequest:
        assert self._login_response, "Attempted api request without authentication."
        return GetCommitmentRequest(
            netuid=self._login_response.netuid,
            identity_name=self._login_response.identity_name,
            hotkey=hotkey,
        )

    async def _get_own_commitment_request(self) -> GetOwnCommitmentRequest:
        assert self._login_response, "Attempted api request without authentication."
        return GetOwnCommitmentRequest(
            netuid=self._login_response.netuid,
            identity_name=self._login_response.identity_name,
        )

    async def _set_commitment_request(
        self, commitment: CommitmentDataBytes | CommitmentDataHex
    ) -> SetCommitmentRequest:
        assert self._login_response, "Attempted api request without authentication."
        return SetCommitmentRequest(
            netuid=self._login_response.netuid,
            identity_name=self._login_response.identity_name,
            commitment=cast(CommitmentDataBytes, commitment),
        )

    async def _get_validators_request(self, block_number: BlockNumber) -> GetValidatorsRequest:
        assert self._login_response, "Attempted api request without authentication."
        return GetValidatorsRequest(
            netuid=self._login_response.netuid,
            identity_name=self._login_response.identity_name,
            block_number=block_number,
        )

    async def _get_latest_validators_request(self) -> GetLatestValidatorsRequest:
        assert self._login_response, "Attempted api request without authentication."
        return GetLatestValidatorsRequest(
            netuid=self._login_response.netuid,
            identity_name=self._login_response.identity_name,
        )
