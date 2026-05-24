import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from functools import partial
from typing import Any, TypeVar

from pylon_client._internal.client.sync.communicators import AbstractCommunicator
from pylon_client._internal.pylon_commons._unstable.requests import (
    GetAllRevealedCommitmentsRequest,
    GetCertificateRequest,
    GetCommitmentRequest,
    GetCommitmentsRequest,
    GetDrandLastStoredRoundRequest,
    GetEvmLogsRequest,
    GetExtrinsicRequest,
    GetLatestBlockInfoRequest,
    GetLatestEvmAssociationsRequest,
    GetLatestNeuronsRequest,
    GetLatestPriceRequest,
    GetLatestPricesRequest,
    GetLatestValidatorsRequest,
    GetNeuronsRequest,
    GetOwnCommitmentRequest,
    GetOwnRevealedCommitmentsRequest,
    GetPriceRequest,
    GetPricesRequest,
    GetRecentNeuronsRequest,
    GetRevealedCommitmentsRequest,
    GetValidatorsRequest,
    GetWeightsStatusRequest,
    PylonRequest,
    SetCommitmentRequest,
    SetRevealedCommitmentRequest,
    SetWeightsRequest,
)
from pylon_client._internal.pylon_commons._unstable.responses import (
    GetAllRevealedCommitmentsResponse,
    GetCertificateResponse,
    GetCommitmentResponse,
    GetCommitmentsResponse,
    GetDrandLastStoredRoundResponse,
    GetEvmLogsResponse,
    GetExtrinsicResponse,
    GetLatestBlockInfoResponse,
    GetLatestEvmAssociationsResponse,
    GetNeuronsResponse,
    GetPriceResponse,
    GetPricesResponse,
    GetRevealedCommitmentsResponse,
    GetValidatorsResponse,
    GetWeightsStatusResponse,
    PylonResponse,
    SetCommitmentResponse,
    SetRevealedCommitmentResponse,
    SetWeightsResponse,
)
from pylon_client._internal.pylon_commons.apiver import ApiVersion
from pylon_client._internal.pylon_commons.exceptions import (
    PylonClosed,
    PylonNetuidMismatch,
)
from pylon_client._internal.pylon_commons.types import (
    BlockNumber,
    CommitmentDataBytes,
    CommitmentDataHex,
    ExtrinsicIndex,
    Hotkey,
    IdentityName,
    MechanismId,
    NetUid,
    Weight,
)
from pylon_client._internal.file_backed_neurons import load_file_backed_neurons

ResponseT = TypeVar("ResponseT", bound=PylonResponse)


class AbstractApi(ABC):
    """
    Class that represents the API available in the service (synchronous).
    It provides the set of methods to query the service endpoints in a simple way.
    """

    api_version: ApiVersion

    def __init__(self, communicator: AbstractCommunicator):
        self._communicator = communicator

    def _send_request(self, request: PylonRequest[ResponseT]) -> ResponseT:
        """
        Sends the request via the communicator, first checking if the communicator is open.

        Raises:
            PylonClosed: When the communicator is closed while calling this method.
        """
        if not self._communicator.is_open:
            raise PylonClosed("The communicator is closed.")
        request.api_version = self.api_version
        return self._communicator.request(request)

    def _file_backed_neurons(self) -> GetNeuronsResponse | None:
        """
        Returns neurons loaded from the configured local `neurons_file` for local development,
        or None when no `neurons_file` is set (i.e. the call should hit the live service).
        """
        neurons_file = self._communicator.config.neurons_file
        if neurons_file:
            return load_file_backed_neurons(neurons_file)
        return None


class AbstractOpenAccessApi(AbstractApi, ABC):
    """
    Open access API for querying Bittensor subnet data via Pylon service without identity authentication.

    This API provides read-only access to the chain data across any subnet.
    Requests require an open access token configured in the client.

    All methods in this API may raise the following exceptions:
        PylonClosed: When the api method is called and the communicator is closed.
        PylonRequestException: When a network or connection error occurs and all retries are exhausted.
            Requests are retried automatically according to the retry configuration.
        PylonResponseException: When the server returns an error response.
        PylonMisconfigured: When the open access token is not configured.
    """

    # Public API

    def get_neurons(self, netuid: NetUid, block_number: BlockNumber) -> GetNeuronsResponse:
        """
        Retrieves neurons for a specific subnet at a given block number.

        Args:
            netuid: The unique identifier of the subnet.
            block_number: The blockchain block number to query neurons at.

        Returns:
            GetNeuronsResponse: containing the block information and a dictionary mapping hotkeys to Neuron objects.
        """
        return self._send_request(self._get_neurons_request(netuid, block_number))

    def get_latest_neurons(self, netuid: NetUid) -> GetNeuronsResponse:
        """
        Retrieves neurons for a specific subnet at the latest available block.

        Args:
            netuid: The unique identifier of the subnet.

        Returns:
            GetNeuronsResponse: containing the latest block information and a dictionary mapping hotkeys to
            Neuron objects.
        """
        if (file_backed := self._file_backed_neurons()) is not None:
            return file_backed
        return self._send_request(self._get_latest_neurons_request(netuid))

    def get_recent_neurons(self, netuid: NetUid) -> GetNeuronsResponse:
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
        if (file_backed := self._file_backed_neurons()) is not None:
            return file_backed
        return self._send_request(self._get_recent_neurons_request(netuid))

    def get_commitments(self, netuid: NetUid) -> GetCommitmentsResponse:
        """
        Retrieves all commitments for a specific subnet at the latest available block.

        Args:
            netuid: The unique identifier of the subnet.

        Returns:
            GetCommitmentsResponse: containing data mapping hotkeys to commitments.
        """
        return self._send_request(self._get_commitments_request(netuid))

    def get_all_revealed_commitments(self, netuid: NetUid) -> GetAllRevealedCommitmentsResponse:
        """
        Retrieves all revealed commitments for a specific subnet at the latest available block.
        Args:
            netuid: The unique identifier of the subnet.

        Returns:
            GetAllRevealedCommitmentsResponse: containing data mapping hotkeys to revealed commitment lists.
        """
        return self._send_request(self._get_all_revealed_commitments_request(netuid))

    def get_commitment(self, netuid: NetUid, hotkey: Hotkey) -> GetCommitmentResponse:
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
        return self._send_request(self._get_commitment_request(netuid, hotkey))

    def get_revealed_commitments(self, netuid: NetUid, hotkey: Hotkey) -> GetRevealedCommitmentsResponse:
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
        return self._send_request(self._get_revealed_commitments_request(netuid, hotkey))

    def get_validators(self, netuid: NetUid, block_number: BlockNumber) -> GetValidatorsResponse:
        """
        Retrieves validators for a specific subnet at a given block number.

        Validators are neurons with validator_permit=True, sorted by total stake in descending order.

        Args:
            netuid: The unique identifier of the subnet.
            block_number: The blockchain block number to query validators at.

        Returns:
            GetValidatorsResponse: containing the block information and a list of validator Neuron objects.
        """
        return self._send_request(self._get_validators_request(netuid, block_number))

    def get_latest_validators(self, netuid: NetUid) -> GetValidatorsResponse:
        """
        Retrieves validators for a specific subnet at the latest available block.

        Validators are neurons with validator_permit=True, sorted by total stake in descending order.

        Args:
            netuid: The unique identifier of the subnet.

        Returns:
            GetValidatorsResponse: containing the latest block information and a list of validator Neuron objects.
        """
        return self._send_request(self._get_latest_validators_request(netuid))

    def get_certificate(self, netuid: NetUid, hotkey: Hotkey) -> GetCertificateResponse:
        """
        Retrieves the certificate for a specific hotkey in a subnet at the latest available block.

        Args:
            netuid: The unique identifier of the subnet.
            hotkey: The hotkey to retrieve the certificate for.

        Returns:
            GetCertificateResponse: containing the certificate's algorithm and public key.

        Raises:
            PylonNotFound: If a certificate could not be found.
        """
        return self._send_request(self._get_certificate_request(netuid, hotkey))

    def get_latest_block_info(self) -> GetLatestBlockInfoResponse:
        """
        Retrieves the latest block information from the chain.

        This is a blockchain-level query that does not require subnet context.

        Returns:
            GetLatestBlockInfoResponse: containing the block number and hash.
        """
        return self._send_request(self._get_latest_block_info_request())

    def get_latest_prices(self) -> GetPricesResponse:
        """
        Retrieves alpha prices (rao) for all subnets at the latest block.
        """
        return self._send_request(self._get_latest_prices_request())

    def get_prices(self, block_number: BlockNumber) -> GetPricesResponse:
        """
        Retrieves alpha prices (rao) for all subnets at a given block.
        """
        return self._send_request(self._get_prices_request(block_number))

    def get_latest_price(self, netuid: NetUid) -> GetPriceResponse:
        """
        Retrieves the alpha price (rao) for a single subnet at the latest block.
        """
        return self._send_request(self._get_latest_price_request(netuid))

    def get_price(self, netuid: NetUid, block_number: BlockNumber) -> GetPriceResponse:
        """
        Retrieves the alpha price (rao) for a single subnet at a given block.
        """
        return self._send_request(self._get_price_request(netuid, block_number))

    def get_extrinsic(self, block_number: BlockNumber, extrinsic_index: ExtrinsicIndex) -> GetExtrinsicResponse:
        """
        Retrieves a decoded extrinsic from a specific block.

        This is a block-level query that does not require subnet context.

        Args:
            block_number: The blockchain block number to query.
            extrinsic_index: The index of the extrinsic within the block.

        Returns:
            GetExtrinsicResponse: containing the full extrinsic data.
        """
        return self._send_request(self._get_extrinsic_request(block_number, extrinsic_index))

    def get_drand_last_stored_round(self) -> GetDrandLastStoredRoundResponse:
        """
        Retrieves the last stored drand round.

        This is a blockchain-level query that does not require subnet context.

        Returns:
            GetDrandLastStoredRoundRequest: containing the last stored round number.
        """
        return self._send_request(self._get_drand_last_stored_round_request())

    def get_latest_evm_associations(self, netuid: NetUid) -> GetLatestEvmAssociationsResponse:
        """
        Retrieves the latest EVM key associations in a subnet at the latest available block

        Returns:
            GetLatestEvmAssociationsResponse: containing data mapping hotkeys to evm key associations.
        """
        return self._send_request(self._get_latest_evm_associations_request(netuid))

    def get_evm_logs(
        self,
        contract_address: evm_types.Address,
        from_block: evm_types.BlockNumber,
        to_block: evm_types.BlockNumber,
        abi: list[dict[str, Any]],
    ) -> GetEvmLogsResponse:
        """
        Retrieves decoded EVM contract logs for a given address and block range.

        Args:
            contract_address: The EVM contract address to query logs for.
            from_block: The starting block number (inclusive).
            to_block: The ending block number (inclusive).
            abi: The contract ABI as a list of dicts, used to decode event logs.

        Returns:
            GetEvmLogsResponse: containing the decoded logs and the queried block range.
        """
        return self._send_request(self._get_evm_logs_request(contract_address, from_block, to_block, abi))

    # Private API

    @abstractmethod
    def _get_neurons_request(self, netuid: NetUid, block_number: BlockNumber) -> GetNeuronsRequest: ...

    @abstractmethod
    def _get_latest_neurons_request(self, netuid: NetUid) -> GetLatestNeuronsRequest: ...

    @abstractmethod
    def _get_recent_neurons_request(self, netuid: NetUid) -> GetRecentNeuronsRequest: ...

    @abstractmethod
    def _get_validators_request(self, netuid: NetUid, block_number: BlockNumber) -> GetValidatorsRequest: ...

    @abstractmethod
    def _get_latest_validators_request(self, netuid: NetUid) -> GetLatestValidatorsRequest: ...

    @abstractmethod
    def _get_commitments_request(self, netuid: NetUid) -> GetCommitmentsRequest: ...

    @abstractmethod
    def _get_all_revealed_commitments_request(self, netuid: NetUid) -> GetAllRevealedCommitmentsRequest: ...

    @abstractmethod
    def _get_commitment_request(self, netuid: NetUid, hotkey: Hotkey) -> GetCommitmentRequest: ...

    @abstractmethod
    def _get_revealed_commitments_request(self, netuid: NetUid, hotkey: Hotkey) -> GetRevealedCommitmentsRequest: ...

    @abstractmethod
    def _get_latest_block_info_request(self) -> GetLatestBlockInfoRequest: ...

    @abstractmethod
    def _get_latest_prices_request(self) -> GetLatestPricesRequest: ...

    @abstractmethod
    def _get_prices_request(self, block_number: BlockNumber) -> GetPricesRequest: ...

    @abstractmethod
    def _get_latest_price_request(self, netuid: NetUid) -> GetLatestPriceRequest: ...

    @abstractmethod
    def _get_price_request(self, netuid: NetUid, block_number: BlockNumber) -> GetPriceRequest: ...

    @abstractmethod
    def _get_extrinsic_request(
        self, block_number: BlockNumber, extrinsic_index: ExtrinsicIndex
    ) -> GetExtrinsicRequest: ...

    @abstractmethod
    def _get_drand_last_stored_round_request(self) -> GetDrandLastStoredRoundRequest: ...

    @abstractmethod
    def _get_latest_evm_associations_request(self, netuid: NetUid) -> GetLatestEvmAssociationsRequest: ...

    @abstractmethod
    def _get_evm_logs_request(
        self,
        contract_address: evm_types.Address,
        from_block: evm_types.BlockNumber,
        to_block: evm_types.BlockNumber,
        abi: list[dict[str, Any]],
    ) -> GetEvmLogsRequest: ...

    @abstractmethod
    def _get_certificate_request(self, netuid: NetUid, hotkey: Hotkey) -> GetCertificateRequest: ...


class AbstractIdentityApi(AbstractApi, ABC):
    """
    Identity-authenticated API for subnet-specific operations.

    This API provides access to read and write operations for a specific subnet associated with
    the configured identity. The subnet is determined automatically from the identity credentials.
    The netuid for the configured identity is fetched lazily on the first request and cached
    for subsequent requests. The cache is refreshed automatically when the server signals
    a netuid mismatch (HTTP 308).

    All methods in this API may raise the following exceptions:
        PylonClosed: When the api method is called and the communicator is closed.
        PylonRequestException: When a network or connection error occurs and all retries are exhausted.
            Requests are retried automatically according to the retry configuration.
        PylonResponseException: When the server returns an error response.
        PylonUnauthorized: When authentication fails by the reason of wrong credentials.
        PylonMisconfigured: When required identity credentials (identity_name and identity_token)
            are not configured.
    """

    def __init__(self, communicator: AbstractCommunicator):
        super().__init__(communicator)
        identity_name = communicator.config.identity_name
        if identity_name is None:
            raise ValueError("IdentityApi requires identity_name to be set in config.")
        self.identity_name: IdentityName = identity_name
        self._netuid: NetUid | None = None
        self._identity_lock = threading.Lock()

    @abstractmethod
    def _fetch_netuid(self) -> None:
        """
        Fetches the netuid for the configured identity from the server and assigns it (together
        with the identity name) to self._netuid and self._identity_name. Called under self._identity_lock.
        """

    @property
    def netuid(self) -> NetUid:
        if self._netuid is None:
            raise AttributeError("Identity netuid accessed before it was resolved.")
        return self._netuid

    def _ensure_netuid(self) -> NetUid:
        with self._identity_lock:
            if self._netuid is None:
                self._fetch_netuid()
            assert self._netuid is not None
            return self._netuid

    def _refetch_netuid_if_stale(self, seen_netuid: NetUid) -> None:
        with self._identity_lock:
            if self._netuid == seen_netuid:
                self._fetch_netuid()

    def _send_identity_request(self, request_factory: Callable[[], PylonRequest[ResponseT]]) -> ResponseT:
        seen_netuid = self._ensure_netuid()
        try:
            return self._send_request(request_factory())
        except PylonNetuidMismatch:
            self._refetch_netuid_if_stale(seen_netuid)
            return self._send_request(request_factory())

    # Public API

    def get_neurons(self, block_number: BlockNumber) -> GetNeuronsResponse:
        """
        Retrieves neurons for the authenticated identity's subnet at a given block number.

        Args:
            block_number: The blockchain block number to query neurons at.

        Returns:
            GetNeuronsResponse containing the block information and a dictionary mapping hotkeys to Neuron objects.
        """
        return self._send_identity_request(partial(self._get_neurons_request, block_number))

    def get_latest_neurons(self) -> GetNeuronsResponse:
        """
        Retrieves neurons for the authenticated identity's subnet at the latest available block.

        Returns:
            GetNeuronsResponse containing the latest block information and a dictionary mapping hotkeys to
            Neuron objects.
        """
        if (file_backed := self._file_backed_neurons()) is not None:
            return file_backed
        return self._send_identity_request(self._get_latest_neurons_request)

    def get_recent_neurons(self) -> GetNeuronsResponse:
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
        if (file_backed := self._file_backed_neurons()) is not None:
            return file_backed
        return self._send_identity_request(self._get_recent_neurons_request)

    def put_weights(
        self, weights: dict[Hotkey, Weight], mechanism_id: MechanismId = MechanismId(0)
    ) -> SetWeightsResponse:
        """
        Submits weights for neurons in the authenticated identity's subnet.

        Weights are applied asynchronously by the Pylon service. The method returns immediately after
        scheduling the weight update, without waiting for blockchain confirmation. The service handles
        commit-reveal or direct weight setting based on subnet hyperparameters.

        Args:
            weights: Dictionary mapping neuron hotkeys to their respective weight values. Weights should
                be normalized (sum to 1.0) and only include neurons that should receive non-zero weights.
            mechanism_id: The ID of the mechanism used for weight setting. Defaults to 0.

        Returns:
            SetWeightsResponse indicating the weights update has been scheduled.
        """
        return self._send_identity_request(partial(self._put_weights_request, weights, mechanism_id))

    def get_weights_status(
        self, block_number: BlockNumber, mechanism_id: MechanismId = MechanismId(0)
    ) -> GetWeightsStatusResponse:
        """
        response: { weights_set: boolean }
        """
        return self._send_identity_request(partial(self._get_weights_status_request, mechanism_id, block_number))

    def get_commitments(self) -> GetCommitmentsResponse:
        """
        Retrieves all commitments for the authenticated identity's subnet at the latest available block.

        Returns:
            GetCommitmentsResponse: containing data mapping hotkeys to data commitments.
        """
        return self._send_identity_request(self._get_commitments_request)

    def get_all_revealed_commitments(self) -> GetAllRevealedCommitmentsResponse:
        """
        Retrieves all revealed commitments for the authenticated identity's subnet at the latest available block.

        Returns:
            GetAllRevealedCommitmentsResponse: containing data mapping hotkeys to revealed commitment lists.
        """
        return self._send_identity_request(self._get_all_revealed_commitments_request)

    def get_commitment(self, hotkey: Hotkey) -> GetCommitmentResponse:
        """
        Retrieves a specific commitment for a hotkey in the authenticated identity's subnet.

        Args:
            hotkey: The hotkey to retrieve the commitment for.

        Returns:
            GetCommitmentResponse: containing a commitment.

        Raises:
            PylonNotFound: If a data commitment could not be found.
        """
        return self._send_identity_request(partial(self._get_commitment_request, hotkey))

    def get_revealed_commitments(self, hotkey: Hotkey) -> GetRevealedCommitmentsResponse:
        """
        Retrieves revealed commitments for a hotkey in the authenticated identity's subnet.

        Args:
            hotkey: The hotkey to retrieve the commitment for.

        Returns:
            GetRevealedCommitmentsResponse: containing a list of its revealed commitments.

        Raises:
            PylonNotFound: If the commitments could not be found.
        """
        return self._send_identity_request(partial(self._get_revealed_commitments_request, hotkey))

    def get_own_commitment(self) -> GetCommitmentResponse:
        """
        Retrieves the commitment for the authenticated identity's own wallet hotkey.

        Returns:
            GetCommitmentResponse: containing a commitment.

        Raises:
            PylonNotFound: If a commitment could not be found.
        """
        return self._send_identity_request(self._get_own_commitment_request)

    def get_own_revealed_commitments(self) -> GetRevealedCommitmentsResponse:
        """
        Retrieves revealed commitments for the authenticated identity's own wallet hotkey.

        Returns:
            GetRevealedCommitmentsResponse: containing a commitment list.

        Raises:
            PylonNotFound: If no commitments could be found.
        """
        return self._send_identity_request(self._get_own_revealed_commitments_request)

    def set_commitment(self, commitment: CommitmentDataBytes | CommitmentDataHex) -> SetCommitmentResponse:
        """
        Sets a commitment (model metadata) on-chain for the authenticated identity's wallet hotkey.

        The commitment is applied asynchronously by the Pylon service. The method returns immediately after
        scheduling the commitment update, without waiting for blockchain confirmation.

        Args:
            commitment: The commitment data to set. Can be bytes or hex string format (with or without 0x prefix).

        Returns:
            SetCommitmentResponse indicating the commitment has been set successfully.
        """
        return self._send_identity_request(partial(self._set_commitment_request, commitment))

    def set_revealed_commitment(self, commitment: str, blocks_until_reveal: int = 360) -> SetRevealedCommitmentResponse:
        """
        Sets a time-encrypted commitment on-chain for the authenticated identity's wallet hotkey.

        The commitment is applied asynchronously by the Pylon service. The method returns immediately after
        scheduling the commitment update, without waiting for blockchain confirmation.

        Args:
            commitment:
            blocks_until_reveal: Number of blocks from now after which the commitment should be revealed. Defaults to 360 blocks.

        Returns:
            SetRevealedCommitmentResponse containing a reveal round number.
        """
        return self._send_identity_request(
            partial(self._set_revealed_commitment_request, commitment, blocks_until_reveal)
        )

    def get_validators(self, block_number: BlockNumber) -> GetValidatorsResponse:
        """
        Retrieves validators for the authenticated identity's subnet at a given block number.

        Validators are neurons with validator_permit=True, sorted by total stake in descending order.

        Args:
            block_number: The blockchain block number to query validators at.

        Returns:
            GetValidatorsResponse: containing the block information and a list of validator Neuron objects.
        """
        return self._send_identity_request(partial(self._get_validators_request, block_number))

    def get_latest_validators(self) -> GetValidatorsResponse:
        """
        Retrieves validators for the authenticated identity's subnet at the latest available block.

        Validators are neurons with validator_permit=True, sorted by total stake in descending order.

        Returns:
            GetValidatorsResponse: containing the latest block information and a list of validator Neuron objects.
        """
        return self._send_identity_request(self._get_latest_validators_request)

    def get_certificate(self, hotkey: Hotkey) -> GetCertificateResponse:
        """
        Retrieves the certificate for a specific hotkey in the authenticated identity's subnet.

        Args:
            hotkey: The hotkey to retrieve the certificate for.

        Returns:
            GetCertificateResponse: containing the certificate's algorithm and public key.

        Raises:
            PylonNotFound: If a certificate could not be found.
        """
        return self._send_identity_request(partial(self._get_certificate_request, hotkey))

    def get_latest_block_info(self) -> GetLatestBlockInfoResponse:
        """
        Retrieves the latest block information from the chain.

        This is a blockchain-level query that does not require subnet context.

        Returns:
            GetLatestBlockInfoResponse: containing the block number and hash.
        """
        return self._send_identity_request(self._get_latest_block_info_request)

    def get_latest_prices(self) -> GetPricesResponse:
        """
        Retrieves alpha prices (rao) for all subnets at the latest block.
        """
        return self._send_identity_request(self._get_latest_prices_request)

    def get_prices(self, block_number: BlockNumber) -> GetPricesResponse:
        """
        Retrieves alpha prices (rao) for all subnets at a given block.
        """
        return self._send_identity_request(partial(self._get_prices_request, block_number))

    def get_latest_price(self) -> GetPriceResponse:
        """
        Retrieves the alpha price (rao) for the identity's subnet at the latest block.
        """
        return self._send_identity_request(self._get_latest_price_request)

    def get_price(self, block_number: BlockNumber) -> GetPriceResponse:
        """
        Retrieves the alpha price (rao) for the identity's subnet at a given block.
        """
        return self._send_identity_request(partial(self._get_price_request, block_number))

    def get_extrinsic(self, block_number: BlockNumber, extrinsic_index: ExtrinsicIndex) -> GetExtrinsicResponse:
        """
        Retrieves a decoded extrinsic from a specific block.

        This is a block-level query that does not require subnet context.

        Args:
            block_number: The blockchain block number to query.
            extrinsic_index: The index of the extrinsic within the block.

        Returns:
            GetExtrinsicResponse: containing the full extrinsic data.
        """
        return self._send_identity_request(partial(self._get_extrinsic_request, block_number, extrinsic_index))

    def get_drand_last_stored_round(self) -> GetDrandLastStoredRoundResponse:
        """
        Retrieves the last stored drand round.

        This is a blockchain-level query that does not require subnet context.

        Returns:
            GetDrandLastStoredRoundRequest: containing the last stored round number.
        """
        return self._send_identity_request(self._get_drand_last_stored_round_request)

    def get_latest_evm_associations(self) -> GetLatestEvmAssociationsResponse:
        """
        Retrieves the latest EVM key associations for the authenticated identity's subnet at the latest available block

        Returns:
            GetLatestEvmAssociationsResponse: containing data mapping hotkeys to evm key associations.
        """
        return self._send_identity_request(self._get_latest_evm_associations_request)

    # Private API

    @abstractmethod
    def _get_neurons_request(self, block_number: BlockNumber) -> GetNeuronsRequest: ...

    @abstractmethod
    def _get_latest_neurons_request(self) -> GetLatestNeuronsRequest: ...

    @abstractmethod
    def _get_recent_neurons_request(self) -> GetRecentNeuronsRequest: ...

    @abstractmethod
    def _put_weights_request(self, weights: dict[Hotkey, Weight], mechanism_id: MechanismId) -> SetWeightsRequest: ...

    @abstractmethod
    def _get_weights_status_request(
        self, mechanism_id: MechanismId, block_number: BlockNumber
    ) -> GetWeightsStatusRequest: ...

    @abstractmethod
    def _get_commitments_request(self) -> GetCommitmentsRequest: ...

    @abstractmethod
    def _get_all_revealed_commitments_request(self) -> GetAllRevealedCommitmentsRequest: ...

    @abstractmethod
    def _get_commitment_request(self, hotkey: Hotkey) -> GetCommitmentRequest: ...

    @abstractmethod
    def _get_revealed_commitments_request(self, hotkey: Hotkey) -> GetRevealedCommitmentsRequest: ...

    @abstractmethod
    def _get_own_commitment_request(self) -> GetOwnCommitmentRequest: ...

    @abstractmethod
    def _get_own_revealed_commitments_request(self) -> GetOwnRevealedCommitmentsRequest: ...

    @abstractmethod
    def _set_commitment_request(self, commitment: CommitmentDataBytes | CommitmentDataHex) -> SetCommitmentRequest: ...

    @abstractmethod
    def _set_revealed_commitment_request(
        self, commitment: str, blocks_until_reveal: int = 360
    ) -> SetRevealedCommitmentRequest: ...

    @abstractmethod
    def _get_validators_request(self, block_number: BlockNumber) -> GetValidatorsRequest: ...

    @abstractmethod
    def _get_latest_validators_request(self) -> GetLatestValidatorsRequest: ...

    @abstractmethod
    def _get_latest_block_info_request(self) -> GetLatestBlockInfoRequest: ...

    @abstractmethod
    def _get_latest_prices_request(self) -> GetLatestPricesRequest: ...

    @abstractmethod
    def _get_prices_request(self, block_number: BlockNumber) -> GetPricesRequest: ...

    @abstractmethod
    def _get_latest_price_request(self) -> GetLatestPriceRequest: ...

    @abstractmethod
    def _get_price_request(self, block_number: BlockNumber) -> GetPriceRequest: ...

    @abstractmethod
    def _get_extrinsic_request(
        self, block_number: BlockNumber, extrinsic_index: ExtrinsicIndex
    ) -> GetExtrinsicRequest: ...

    @abstractmethod
    def _get_drand_last_stored_round_request(self) -> GetDrandLastStoredRoundRequest: ...

    @abstractmethod
    def _get_latest_evm_associations_request(self) -> GetLatestEvmAssociationsRequest: ...

    @abstractmethod
    def _get_certificate_request(self, hotkey: Hotkey) -> GetCertificateRequest: ...
