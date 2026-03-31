import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from functools import partial
from typing import Generic, NewType, TypeVar

from pylon_client._internal.client.asynchronous.communicators import AbstractAsyncCommunicator
from pylon_client._internal.pylon_commons._unstable.requests import (
    GetAllRevealedCommitmentsRequest,
    GetCommitmentRequest,
    GetCommitmentsRequest,
    GetDrandLastStoredRoundRequest,
    GetExtrinsicRequest,
    GetLatestBlockInfoRequest,
    GetLatestNeuronsRequest,
    GetLatestValidatorsRequest,
    GetNeuronsRequest,
    GetOwnCommitmentRequest,
    GetOwnRevealedCommitmentsRequest,
    GetRecentNeuronsRequest,
    GetRevealedCommitmentsRequest,
    GetValidatorsRequest,
    PylonRequest,
    SetCommitmentRequest,
    SetRevealedCommitmentRequest,
    SetWeightsRequest,
)
from pylon_client._internal.pylon_commons._unstable.responses import (
    GetAllRevealedCommitmentsResponse,
    GetCommitmentResponse,
    GetCommitmentsResponse,
    GetDrandLastStoredRoundResponse,
    GetExtrinsicResponse,
    GetLatestBlockInfoResponse,
    GetNeuronsResponse,
    GetRevealedCommitmentsResponse,
    GetValidatorsResponse,
    LoginResponse,
    PylonResponse,
    SetCommitmentResponse,
    SetRevealedCommitmentResponse,
    SetWeightsResponse,
)
from pylon_client._internal.pylon_commons.apiver import ApiVersion
from pylon_client._internal.pylon_commons.exceptions import (
    PylonClosed,
    PylonForbidden,
    PylonUnauthorized,
)
from pylon_client._internal.pylon_commons.types import (
    BlockNumber,
    CommitmentDataBytes,
    CommitmentDataHex,
    ExtrinsicIndex,
    Hotkey,
    NetUid,
    Weight,
)

ResponseT = TypeVar("ResponseT", bound=PylonResponse)
LoginResponseT = TypeVar("LoginResponseT", bound=LoginResponse)
LoginGeneration = NewType("LoginGeneration", int)
ALWAYS_FRESH_GENERATION = LoginGeneration(-1)


class AbstractAsyncApi(Generic[LoginResponseT], ABC):
    """
    Class that represents the API available in the service.
    It provides the set of methods to query the service endpoints in a simple way.
    The class takes care of authentication and re-authentication.
    """

    api_version: ApiVersion

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
        request.api_version = self.api_version
        return await self._communicator.request(request)

    async def _authenticated_request(
        self,
        request_factory: Callable[[], Awaitable[PylonRequest[ResponseT]]],
        stale_generation: LoginGeneration = ALWAYS_FRESH_GENERATION,
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
        PylonRequestException: When a network or connection error occurs and all retries are exhausted.
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
            GetCommitmentsResponse: containing data mapping hotkeys to commitments.
        """
        return await self._send_authenticated_request(partial(self._get_commitments_request, netuid))

    async def get_all_revealed_commitments(self, netuid: NetUid) -> GetAllRevealedCommitmentsResponse:
        """
        Retrieves all revealed commitments for a specific subnet at the latest available block.

        Args:
            netuid: The unique identifier of the subnet.

        Returns:
            GetAllRevealedCommitmentsResponse: containing data mapping hotkeys to revealed commitment lists.
        """
        return await self._send_authenticated_request(partial(self._get_all_revealed_commitments_request, netuid))

    async def get_commitment(self, netuid: NetUid, hotkey: Hotkey) -> GetCommitmentResponse:
        """
        Retrieves a specific commitment for a hotkey in a subnet at the latest available block.

        Args:
            netuid: The unique identifier of the subnet.
            hotkey: The hotkey to retrieve the commitment for.

        Returns:
            GetCommitmentResponse: containing a commitment.

        Throws:
            PylonNotFound: If a commitment could not be found.
        """
        return await self._send_authenticated_request(partial(self._get_commitment_request, netuid, hotkey))

    async def get_revealed_commitments(self, netuid: NetUid, hotkey: Hotkey) -> GetRevealedCommitmentsResponse:
        """
        Retrieves revealed commitments for a hotkey in a subnet at the latest available block.

        Args:
            netuid: The unique identifier of the subnet.
            hotkey: The hotkey to retrieve the commitment for.

        Returns:
            GetRevealedCommitmentResponse: containing revealed commitments.

        Throws:
            PylonNotFound: If no commitments could be found.
        """
        return await self._send_authenticated_request(partial(self._get_revealed_commitments_request, netuid, hotkey))

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

    async def get_latest_block_info(self) -> GetLatestBlockInfoResponse:
        """
        Retrieves the latest block information from the chain.

        This is a blockchain-level query that does not require subnet context.

        Returns:
            GetLatestBlockInfoResponse: containing the block number and hash.
        """
        return await self._send_authenticated_request(self._get_latest_block_info_request)

    async def get_extrinsic(self, block_number: BlockNumber, extrinsic_index: ExtrinsicIndex) -> GetExtrinsicResponse:
        """
        Retrieves a decoded extrinsic from a specific block.

        This is a block-level query that does not require subnet context.

        Args:
            block_number: The blockchain block number to query.
            extrinsic_index: The index of the extrinsic within the block.

        Returns:
            GetExtrinsicResponse: containing the full extrinsic data.
        """
        return await self._send_authenticated_request(
            partial(self._get_extrinsic_request, block_number, extrinsic_index)
        )

    async def get_drand_last_stored_round(self) -> GetDrandLastStoredRoundResponse:
        """
        Retrieves the last stored drand round from the service.

        This is a blockchain-level query that does not require subnet context.

        Returns:
            GetDrandLastStoredRoundRequest: containing the last stored round number.
        """
        return await self._send_authenticated_request(self._get_drand_last_stored_round_request)

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
    async def _get_all_revealed_commitments_request(self, netuid: NetUid) -> GetAllRevealedCommitmentsRequest: ...

    @abstractmethod
    async def _get_commitment_request(self, netuid: NetUid, hotkey: Hotkey) -> GetCommitmentRequest: ...

    @abstractmethod
    async def _get_revealed_commitments_request(
        self, netuid: NetUid, hotkey: Hotkey
    ) -> GetRevealedCommitmentsRequest: ...

    @abstractmethod
    async def _get_latest_block_info_request(self) -> GetLatestBlockInfoRequest: ...

    @abstractmethod
    async def _get_extrinsic_request(
        self, block_number: BlockNumber, extrinsic_index: ExtrinsicIndex
    ) -> GetExtrinsicRequest: ...

    @abstractmethod
    async def _get_drand_last_stored_round_request(self) -> GetDrandLastStoredRoundRequest: ...


class AbstractAsyncIdentityApi(AbstractAsyncApi[LoginResponseT], ABC):
    """
    Identity-authenticated API for subnet-specific operations.

    This API provides access to read and write operations for a specific subnet associated with
    the configured identity. The subnet is determined automatically from the identity credentials.
    Authentication is performed on the first request and cached for subsequent requests.
    The API automatically re-authenticates when sessions expire or authentication errors occur.

    All methods in this API may raise the following exceptions:
        PylonClosed: When the api method is called and the communicator is closed.
        PylonRequestException: When a network or connection error occurs and all retries are exhausted.
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
            GetCommitmentsResponse: containing data mapping hotkeys to data commitments.
        """
        return await self._send_authenticated_request(self._get_commitments_request)

    async def get_all_revealed_commitments(self) -> GetAllRevealedCommitmentsResponse:
        """
        Retrieves all revealed commitments for the authenticated identity's subnet at the latest available block.

        Returns:
            GetAllRevealedCommitmentsResponse: containing data mapping hotkeys to revealed commitment lists.
        """
        return await self._send_authenticated_request(self._get_all_revealed_commitments_request)

    async def get_commitment(self, hotkey: Hotkey) -> GetCommitmentResponse:
        """
        Retrieves a specific commitment for a hotkey in the authenticated identity's subnet.

        Args:
            hotkey: The hotkey to retrieve the commitment for.

        Returns:
            GetCommitmentResponse: containing a commitment.

        Raises:
            PylonNotFound: If a data commitment could not be found.
        """
        return await self._send_authenticated_request(partial(self._get_commitment_request, hotkey))

    async def get_revealed_commitments(self, hotkey: Hotkey) -> GetRevealedCommitmentsResponse:
        """
        Retrieves revealed commitments for a hotkey in the authenticated identity's subnet.

        Args:
            hotkey: The hotkey to retrieve the commitment for.

        Returns:
            GetRevealedCommitmentsResponse: containing a list of its revealed commitments.

        Raises:
            PylonNotFound: If the commitments could not be found.
        """
        return await self._send_authenticated_request(partial(self._get_revealed_commitments_request, hotkey))

    async def get_own_commitment(self) -> GetCommitmentResponse:
        """
        Retrieves the commitment for the authenticated identity's own wallet hotkey.

        Returns:
            GetCommitmentResponse: containing a commitment.

        Raises:
            PylonNotFound: If a commitment could not be found.
        """
        return await self._send_authenticated_request(self._get_own_commitment_request)

    async def get_own_revealed_commitments(self) -> GetRevealedCommitmentsResponse:
        """
        Retrieves revealed commitments for the authenticated identity's own wallet hotkey.

        Returns:
            GetRevealedCommitmentsResponse: containing a commitment list.

        Raises:
            PylonNotFound: If no commitments could be found.
        """
        return await self._send_authenticated_request(self._get_own_revealed_commitments_request)

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

    async def set_revealed_commitment(
        self, commitment: str, blocks_until_reveal: int = 360, block_time: int | float = 12
    ) -> SetRevealedCommitmentResponse:
        """
        Sets a commitment (model metadata) on-chain for the authenticated identity's wallet hotkey.

        The commitment is applied asynchronously by the Pylon service. The method returns immediately after
        scheduling the commitment update, without waiting for blockchain confirmation.

        Args:
            commitment:
            blocks_until_reveal: Number of blocks from now after which the commitment should be revealed. Defaults to 360 blocks.
            block_time: Average block time in seconds. Defaults to 12 seconds.

        Returns:
            SetRevealedCommitmentResponse containing a reveal round number.
        """
        return await self._send_authenticated_request(
            partial(self._set_revealed_commitment_request, commitment, blocks_until_reveal, block_time)
        )

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

    async def get_latest_block_info(self) -> GetLatestBlockInfoResponse:
        """
        Retrieves the latest block information from the chain.

        This is a blockchain-level query that does not require subnet context.

        Returns:
            GetLatestBlockInfoResponse: containing the block number and hash.
        """
        return await self._send_authenticated_request(self._get_latest_block_info_request)

    async def get_extrinsic(self, block_number: BlockNumber, extrinsic_index: ExtrinsicIndex) -> GetExtrinsicResponse:
        """
        Retrieves a decoded extrinsic from a specific block.

        This is a block-level query that does not require subnet context.

        Args:
            block_number: The blockchain block number to query.
            extrinsic_index: The index of the extrinsic within the block.

        Returns:
            GetExtrinsicResponse: containing the full extrinsic data.
        """
        return await self._send_authenticated_request(
            partial(self._get_extrinsic_request, block_number, extrinsic_index)
        )

    async def get_drand_last_stored_round(self) -> GetDrandLastStoredRoundResponse:
        """
        Retrieves the last stored drand round from the service.

        This is a blockchain-level query that does not require subnet context.

        Returns:
            GetDrandLastStoredRoundRequest: containing the last stored round number.
        """
        return await self._send_authenticated_request(self._get_drand_last_stored_round_request)

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
    async def _get_all_revealed_commitments_request(self) -> GetAllRevealedCommitmentsRequest: ...

    @abstractmethod
    async def _get_commitment_request(self, hotkey: Hotkey) -> GetCommitmentRequest: ...

    @abstractmethod
    async def _get_revealed_commitments_request(self, hotkey: Hotkey) -> GetRevealedCommitmentsRequest: ...

    @abstractmethod
    async def _get_own_commitment_request(self) -> GetOwnCommitmentRequest: ...

    @abstractmethod
    async def _get_own_revealed_commitments_request(self) -> GetOwnRevealedCommitmentsRequest: ...

    @abstractmethod
    async def _set_commitment_request(
        self, commitment: CommitmentDataBytes | CommitmentDataHex
    ) -> SetCommitmentRequest: ...

    @abstractmethod
    async def _set_revealed_commitment_request(
        self, commitment: str, blocks_until_reveal: int = 360, block_time: int | float = 12
    ) -> SetRevealedCommitmentRequest: ...

    @abstractmethod
    async def _get_validators_request(self, block_number: BlockNumber) -> GetValidatorsRequest: ...

    @abstractmethod
    async def _get_latest_validators_request(self) -> GetLatestValidatorsRequest: ...

    @abstractmethod
    async def _get_latest_block_info_request(self) -> GetLatestBlockInfoRequest: ...

    @abstractmethod
    async def _get_extrinsic_request(
        self, block_number: BlockNumber, extrinsic_index: ExtrinsicIndex
    ) -> GetExtrinsicRequest: ...

    @abstractmethod
    async def _get_drand_last_stored_round_request(self) -> GetDrandLastStoredRoundRequest: ...
