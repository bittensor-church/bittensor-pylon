from functools import partial

from pylon_client._internal.api._unstable.sync.api import IdentityApi as UnstableIdentityApi
from pylon_client._internal.api._unstable.sync.api import OpenAccessApi as UnstableOpenAccessApi
from pylon_client._internal.pylon_commons.apiver import ApiVersion
from pylon_client._internal.pylon_commons.types import Hotkey, NetUid, Weight
from pylon_client._internal.pylon_commons.v1.requests import (
    GetCommitmentRequest,
    GetCommitmentsRequest,
    GetOwnCommitmentRequest,
    SetWeightsRequest,
)
from pylon_client._internal.pylon_commons.v1.responses import (
    GetCommitmentResponse,
    GetCommitmentsResponse,
    SetWeightsResponse,
)


class OpenAccessApi(UnstableOpenAccessApi):
    api_version = ApiVersion.V1

    def get_commitments(self, netuid: NetUid) -> GetCommitmentsResponse:  # type: ignore[reportIncompatibleMethodOverride]
        """
        Retrieves all hex data commitments for the authenticated identity's subnet at the latest available block.
        Does not include timelock encrypted commitments.

        Returns:
            GetCommitmentsResponse: containing data mapping hotkeys to data commitments.
        """
        return self._send_request(self._get_commitments_request(netuid))

    def get_commitment(self, netuid: NetUid, hotkey: Hotkey) -> GetCommitmentResponse:  # type: ignore[reportIncompatibleMethodOverride]
        """
        Retrieves a hex data commitment for a hotkey in a subnet at the latest available block.

        Args:
            netuid: The unique identifier of the subnet.
            hotkey: The hotkey to retrieve the commitment for.

        Returns:
            GetCommitmentResponse: containing a commitment.

        Throws:
            PylonNotFound: If a commitment could not be found or there is only a timelock encrypted commitment.
        """
        return self._send_request(self._get_commitment_request(netuid, hotkey))

    def _get_commitments_request(self, netuid: NetUid) -> GetCommitmentsRequest:  # type: ignore[reportIncompatibleMethodOverride]
        return GetCommitmentsRequest(netuid=netuid)

    def _get_commitment_request(self, netuid: NetUid, hotkey: Hotkey) -> GetCommitmentRequest:  # type: ignore[reportIncompatibleMethodOverride]
        return GetCommitmentRequest(netuid=netuid, hotkey=hotkey)


class IdentityApi(UnstableIdentityApi):
    api_version = ApiVersion.V1

    def put_weights(self, weights: dict[Hotkey, Weight]) -> SetWeightsResponse:  # type: ignore[reportIncompatibleMethodOverride]
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
        return self._send_identity_request(partial(self._put_weights_request, weights))

    def get_commitments(self) -> GetCommitmentsResponse:  # type: ignore[reportIncompatibleMethodOverride]
        """
        Retrieves all hex data commitments for the authenticated identity's subnet at the latest available block.
        Does not include timelock encrypted commitments.

        Returns:
            GetCommitmentsResponse: containing data mapping hotkeys to data commitments.
        """
        return self._send_identity_request(self._get_commitments_request)

    def get_commitment(self, hotkey: Hotkey) -> GetCommitmentResponse:  # type: ignore[reportIncompatibleMethodOverride]
        """
        Retrieves a hex data commitment for a hotkey in the authenticated identity's subnet.

        Args:
            hotkey: The hotkey to retrieve the commitment for.

        Returns:
            GetCommitmentResponse: containing a commitment.

        Raises:
            PylonNotFound: If a data commitment could not be found or there is only a timelock encrypted commitment.
        """
        return self._send_identity_request(partial(self._get_commitment_request, hotkey))

    def get_own_commitment(self) -> GetCommitmentResponse:  # type: ignore[reportIncompatibleMethodOverride]
        """
        Retrieves a hex data commitment for the authenticated identity's own wallet hotkey.

        Returns:
            GetCommitmentResponse: containing a commitment.

        Raises:
            PylonNotFound: If a commitment could not be found or there is only a timelock encrypted commitment.
        """
        return self._send_identity_request(self._get_own_commitment_request)

    def _put_weights_request(self, weights: dict[Hotkey, Weight]) -> SetWeightsRequest:  # type: ignore[reportIncompatibleMethodOverride]
        return SetWeightsRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
            weights=weights,
        )

    def _get_commitments_request(self) -> GetCommitmentsRequest:  # type: ignore[reportIncompatibleMethodOverride]
        return GetCommitmentsRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
        )

    def _get_commitment_request(self, hotkey: Hotkey) -> GetCommitmentRequest:  # type: ignore[reportIncompatibleMethodOverride]
        return GetCommitmentRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
            hotkey=hotkey,
        )

    def _get_own_commitment_request(self) -> GetOwnCommitmentRequest:  # type: ignore[reportIncompatibleMethodOverride]
        return GetOwnCommitmentRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
        )
