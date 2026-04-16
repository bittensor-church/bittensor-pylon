from typing import cast

from pylon_client._internal.api.abstract_sync import (
    AbstractIdentityApi,
    AbstractOpenAccessApi,
)
from pylon_client._internal.pylon_commons._unstable.requests import (
    GetAllRevealedCommitmentsRequest,
    GetCommitmentRequest,
    GetCommitmentsRequest,
    GetDrandLastStoredRoundRequest,
    GetExtrinsicRequest,
    GetIdentitiesRequest,
    GetLatestBlockInfoRequest,
    GetLatestNeuronsRequest,
    GetLatestValidatorsRequest,
    GetNeuronsRequest,
    GetOwnCommitmentRequest,
    GetOwnRevealedCommitmentsRequest,
    GetRecentNeuronsRequest,
    GetRevealedCommitmentsRequest,
    GetValidatorsRequest,
    SetCommitmentRequest,
    SetRevealedCommitmentRequest,
    SetWeightsRequest,
)
from pylon_client._internal.pylon_commons.apiver import ApiVersion
from pylon_client._internal.pylon_commons.exceptions import PylonMisconfigured
from pylon_client._internal.pylon_commons.types import (
    BlockNumber,
    CommitmentDataBytes,
    CommitmentDataHex,
    ExtrinsicIndex,
    Hotkey,
    NetUid,
    RevealedCommitmentData,
    Weight,
)


class OpenAccessApi(AbstractOpenAccessApi):
    api_version = ApiVersion.UNSTABLE

    def _get_neurons_request(self, netuid: NetUid, block_number: BlockNumber) -> GetNeuronsRequest:
        return GetNeuronsRequest(
            netuid=netuid,
            block_number=block_number,
        )

    def _get_latest_neurons_request(self, netuid: NetUid) -> GetLatestNeuronsRequest:
        return GetLatestNeuronsRequest(netuid=netuid)

    def _get_recent_neurons_request(self, netuid: NetUid) -> GetRecentNeuronsRequest:
        return GetRecentNeuronsRequest(netuid=netuid)

    def _get_commitments_request(self, netuid: NetUid) -> GetCommitmentsRequest:
        return GetCommitmentsRequest(netuid=netuid)

    def _get_all_revealed_commitments_request(self, netuid: NetUid) -> GetAllRevealedCommitmentsRequest:
        return GetAllRevealedCommitmentsRequest(netuid=netuid)

    def _get_commitment_request(self, netuid: NetUid, hotkey: Hotkey) -> GetCommitmentRequest:
        return GetCommitmentRequest(netuid=netuid, hotkey=hotkey)

    def _get_revealed_commitments_request(self, netuid: NetUid, hotkey: Hotkey) -> GetRevealedCommitmentsRequest:
        return GetRevealedCommitmentsRequest(netuid=netuid, hotkey=hotkey)

    def _get_validators_request(self, netuid: NetUid, block_number: BlockNumber) -> GetValidatorsRequest:
        return GetValidatorsRequest(netuid=netuid, block_number=block_number)

    def _get_latest_validators_request(self, netuid: NetUid) -> GetLatestValidatorsRequest:
        return GetLatestValidatorsRequest(netuid=netuid)

    def _get_latest_block_info_request(self) -> GetLatestBlockInfoRequest:
        return GetLatestBlockInfoRequest()

    def _get_extrinsic_request(self, block_number: BlockNumber, extrinsic_index: ExtrinsicIndex) -> GetExtrinsicRequest:
        return GetExtrinsicRequest(block_number=block_number, extrinsic_index=extrinsic_index)

    def _get_drand_last_stored_round_request(self) -> GetDrandLastStoredRoundRequest:
        return GetDrandLastStoredRoundRequest()


class IdentityApi(AbstractIdentityApi):
    api_version = ApiVersion.UNSTABLE

    def _fetch_netuid(self) -> None:
        config = self._communicator.config
        if not config.identity_name or not config.identity_token:
            raise PylonMisconfigured("Can not use identity api - no identity name or token provided in config.")
        response = self._send_request(GetIdentitiesRequest())
        if config.identity_name not in response.identities:
            raise PylonMisconfigured(f"Identity '{config.identity_name}' is not configured on the server.")
        self._identity_name = config.identity_name
        self._netuid = response.identities[config.identity_name]

    def _get_neurons_request(self, block_number: BlockNumber) -> GetNeuronsRequest:
        return GetNeuronsRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
            block_number=block_number,
        )

    def _get_latest_neurons_request(self) -> GetLatestNeuronsRequest:
        return GetLatestNeuronsRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
        )

    def _get_recent_neurons_request(self) -> GetRecentNeuronsRequest:
        return GetRecentNeuronsRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
        )

    def _put_weights_request(self, weights: dict[Hotkey, Weight]) -> SetWeightsRequest:
        return SetWeightsRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
            weights=weights,
        )

    def _get_commitments_request(self) -> GetCommitmentsRequest:
        return GetCommitmentsRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
        )

    def _get_all_revealed_commitments_request(self) -> GetAllRevealedCommitmentsRequest:
        return GetAllRevealedCommitmentsRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
        )

    def _get_commitment_request(self, hotkey: Hotkey) -> GetCommitmentRequest:
        return GetCommitmentRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
            hotkey=hotkey,
        )

    def _get_revealed_commitments_request(self, hotkey: Hotkey) -> GetRevealedCommitmentsRequest:
        return GetRevealedCommitmentsRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
            hotkey=hotkey,
        )

    def _get_own_commitment_request(self) -> GetOwnCommitmentRequest:
        return GetOwnCommitmentRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
        )

    def _get_own_revealed_commitments_request(self) -> GetOwnRevealedCommitmentsRequest:
        return GetOwnRevealedCommitmentsRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
        )

    def _set_commitment_request(self, commitment: CommitmentDataBytes | CommitmentDataHex) -> SetCommitmentRequest:
        return SetCommitmentRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
            commitment=cast(CommitmentDataBytes, commitment),
        )

    def _set_revealed_commitment_request(
        self, commitment: str, blocks_until_reveal: int = 360, block_time: int | float = 12
    ) -> SetRevealedCommitmentRequest:
        return SetRevealedCommitmentRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
            commitment=RevealedCommitmentData(commitment),
            blocks_until_reveal=blocks_until_reveal,
            block_time=block_time,
        )

    def _get_validators_request(self, block_number: BlockNumber) -> GetValidatorsRequest:
        return GetValidatorsRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
            block_number=block_number,
        )

    def _get_latest_validators_request(self) -> GetLatestValidatorsRequest:
        return GetLatestValidatorsRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
        )

    def _get_latest_block_info_request(self) -> GetLatestBlockInfoRequest:
        return GetLatestBlockInfoRequest()

    def _get_extrinsic_request(self, block_number: BlockNumber, extrinsic_index: ExtrinsicIndex) -> GetExtrinsicRequest:
        return GetExtrinsicRequest(block_number=block_number, extrinsic_index=extrinsic_index)

    def _get_drand_last_stored_round_request(self) -> GetDrandLastStoredRoundRequest:
        return GetDrandLastStoredRoundRequest()
