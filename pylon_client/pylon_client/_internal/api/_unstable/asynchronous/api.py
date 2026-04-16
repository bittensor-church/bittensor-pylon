from typing import cast

from pylon_client._internal.api.abstract_async import (
    AbstractAsyncIdentityApi,
    AbstractAsyncOpenAccessApi,
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


class AsyncOpenAccessApi(AbstractAsyncOpenAccessApi):
    api_version = ApiVersion.UNSTABLE

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

    async def _get_all_revealed_commitments_request(self, netuid: NetUid) -> GetAllRevealedCommitmentsRequest:
        return GetAllRevealedCommitmentsRequest(netuid=netuid)

    async def _get_commitment_request(self, netuid: NetUid, hotkey: Hotkey) -> GetCommitmentRequest:
        return GetCommitmentRequest(netuid=netuid, hotkey=hotkey)

    async def _get_revealed_commitments_request(self, netuid: NetUid, hotkey: Hotkey) -> GetRevealedCommitmentsRequest:
        return GetRevealedCommitmentsRequest(netuid=netuid, hotkey=hotkey)

    async def _get_validators_request(self, netuid: NetUid, block_number: BlockNumber) -> GetValidatorsRequest:
        return GetValidatorsRequest(netuid=netuid, block_number=block_number)

    async def _get_latest_validators_request(self, netuid: NetUid) -> GetLatestValidatorsRequest:
        return GetLatestValidatorsRequest(netuid=netuid)

    async def _get_latest_block_info_request(self) -> GetLatestBlockInfoRequest:
        return GetLatestBlockInfoRequest()

    async def _get_extrinsic_request(
        self, block_number: BlockNumber, extrinsic_index: ExtrinsicIndex
    ) -> GetExtrinsicRequest:
        return GetExtrinsicRequest(block_number=block_number, extrinsic_index=extrinsic_index)

    async def _get_drand_last_stored_round_request(self) -> GetDrandLastStoredRoundRequest:
        return GetDrandLastStoredRoundRequest()


class AsyncIdentityApi(AbstractAsyncIdentityApi):
    api_version = ApiVersion.UNSTABLE

    async def _fetch_netuid(self) -> None:
        response = await self._send_request(GetIdentitiesRequest())
        if self.identity_name not in response.identities:
            raise PylonMisconfigured(f"Identity '{self.identity_name}' is not configured on the server.")
        self._netuid = response.identities[self.identity_name]

    async def _get_neurons_request(self, block_number: BlockNumber) -> GetNeuronsRequest:
        return GetNeuronsRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
            block_number=block_number,
        )

    async def _get_latest_neurons_request(self) -> GetLatestNeuronsRequest:
        return GetLatestNeuronsRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
        )

    async def _get_recent_neurons_request(self) -> GetRecentNeuronsRequest:
        return GetRecentNeuronsRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
        )

    async def _put_weights_request(self, weights: dict[Hotkey, Weight]) -> SetWeightsRequest:
        return SetWeightsRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
            weights=weights,
        )

    async def _get_commitments_request(self) -> GetCommitmentsRequest:
        return GetCommitmentsRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
        )

    async def _get_all_revealed_commitments_request(self) -> GetAllRevealedCommitmentsRequest:
        return GetAllRevealedCommitmentsRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
        )

    async def _get_commitment_request(self, hotkey: Hotkey) -> GetCommitmentRequest:
        return GetCommitmentRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
            hotkey=hotkey,
        )

    async def _get_revealed_commitments_request(self, hotkey: Hotkey) -> GetRevealedCommitmentsRequest:
        return GetRevealedCommitmentsRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
            hotkey=hotkey,
        )

    async def _get_own_commitment_request(self) -> GetOwnCommitmentRequest:
        return GetOwnCommitmentRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
        )

    async def _get_own_revealed_commitments_request(self) -> GetOwnRevealedCommitmentsRequest:
        return GetOwnRevealedCommitmentsRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
        )

    async def _set_commitment_request(
        self, commitment: CommitmentDataBytes | CommitmentDataHex
    ) -> SetCommitmentRequest:
        return SetCommitmentRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
            commitment=cast(CommitmentDataBytes, commitment),
        )

    async def _set_revealed_commitment_request(
        self, commitment: str, blocks_until_reveal: int = 360, block_time: int | float = 12
    ) -> SetRevealedCommitmentRequest:
        return SetRevealedCommitmentRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
            commitment=RevealedCommitmentData(commitment),
            blocks_until_reveal=blocks_until_reveal,
            block_time=block_time,
        )

    async def _get_validators_request(self, block_number: BlockNumber) -> GetValidatorsRequest:
        return GetValidatorsRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
            block_number=block_number,
        )

    async def _get_latest_validators_request(self) -> GetLatestValidatorsRequest:
        return GetLatestValidatorsRequest(
            netuid=self.netuid,
            identity_name=self.identity_name,
        )

    async def _get_latest_block_info_request(self) -> GetLatestBlockInfoRequest:
        return GetLatestBlockInfoRequest()

    async def _get_extrinsic_request(
        self, block_number: BlockNumber, extrinsic_index: ExtrinsicIndex
    ) -> GetExtrinsicRequest:
        return GetExtrinsicRequest(block_number=block_number, extrinsic_index=extrinsic_index)

    async def _get_drand_last_stored_round_request(self) -> GetDrandLastStoredRoundRequest:
        return GetDrandLastStoredRoundRequest()
