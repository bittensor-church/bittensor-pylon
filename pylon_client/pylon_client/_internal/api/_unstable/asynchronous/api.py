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
    GetLatestBlockInfoRequest,
    GetLatestNeuronsRequest,
    GetLatestValidatorsRequest,
    GetNeuronsRequest,
    GetOwnCommitmentRequest,
    GetOwnRevealedCommitmentsRequest,
    GetRecentNeuronsRequest,
    GetRevealedCommitmentsRequest,
    GetValidatorsRequest,
    IdentityLoginRequest,
    SetCommitmentRequest,
    SetRevealedCommitmentRequest,
    SetWeightsRequest,
)
from pylon_client._internal.pylon_commons._unstable.responses import (
    IdentityLoginResponse,
    OpenAccessLoginResponse,
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


class AsyncOpenAccessApi(AbstractAsyncOpenAccessApi[OpenAccessLoginResponse]):
    api_version = ApiVersion.UNSTABLE

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


class AsyncIdentityApi(AbstractAsyncIdentityApi[IdentityLoginResponse]):
    api_version = ApiVersion.UNSTABLE

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

    async def _get_all_revealed_commitments_request(self) -> GetAllRevealedCommitmentsRequest:
        assert self._login_response, "Attempted api request without authentication."
        return GetAllRevealedCommitmentsRequest(
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

    async def _get_revealed_commitments_request(self, hotkey: Hotkey) -> GetRevealedCommitmentsRequest:
        assert self._login_response, "Attempted api request without authentication."
        return GetRevealedCommitmentsRequest(
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

    async def _get_own_revealed_commitments_request(self) -> GetOwnRevealedCommitmentsRequest:
        assert self._login_response, "Attempted api request without authentication."
        return GetOwnRevealedCommitmentsRequest(
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

    async def _set_revealed_commitment_request(
        self, commitment: str, blocks_until_reveal: int = 360, block_time: int | float = 12
    ) -> SetRevealedCommitmentRequest:
        assert self._login_response, "Attempted api request without authentication."
        return SetRevealedCommitmentRequest(
            netuid=self._login_response.netuid,
            identity_name=self._login_response.identity_name,
            commitment=RevealedCommitmentData(commitment),
            blocks_until_reveal=blocks_until_reveal,
            block_time=block_time,
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

    async def _get_latest_block_info_request(self) -> GetLatestBlockInfoRequest:
        return GetLatestBlockInfoRequest()

    async def _get_extrinsic_request(
        self, block_number: BlockNumber, extrinsic_index: ExtrinsicIndex
    ) -> GetExtrinsicRequest:
        return GetExtrinsicRequest(block_number=block_number, extrinsic_index=extrinsic_index)

    async def _get_drand_last_stored_round_request(self) -> GetDrandLastStoredRoundRequest:
        return GetDrandLastStoredRoundRequest()
