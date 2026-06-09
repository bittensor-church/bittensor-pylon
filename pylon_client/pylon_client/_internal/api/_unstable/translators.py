from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from httpx import Request

from pylon_client._internal.pylon_commons._unstable.endpoints import Endpoint as EndpointUnstable
from pylon_client._internal.pylon_commons._unstable.requests import (
    AuthenticatedPylonRequest,
    GetAllRevealedCommitmentsRequest,
    GetCommitmentRequest,
    GetCommitmentsRequest,
    GetDrandLastStoredRoundRequest,
    GetEvmLogsRequest,
    GetExtrinsicRequest,
    GetIdentitiesRequest,
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
from pylon_client._internal.pylon_commons.endpoints import Endpoint
from pylon_client._internal.translators import AbstractRequestTranslator

if TYPE_CHECKING:
    from pylon_client._internal.client.asynchronous.communicators import AsyncHttpCommunicator
    from pylon_client._internal.client.sync.communicators import HttpCommunicator

HttpCommunicatorT = TypeVar("HttpCommunicatorT", bound="HttpCommunicator | AsyncHttpCommunicator")


class HttpTranslator(AbstractRequestTranslator[Request, HttpCommunicatorT]):
    """
    Translates PylonRequests into httpx Requests using _unstable API endpoints.
    """

    _endpoint_cls = EndpointUnstable

    @staticmethod
    def _get_auth_headers(request: PylonRequest, communicator: HttpCommunicatorT) -> dict[str, str]:
        if isinstance(request, AuthenticatedPylonRequest):
            if request.identity_name is not None:
                if communicator.config.identity_token:
                    return {"Authorization": f"Bearer {communicator.config.identity_token}"}
            elif communicator.config.open_access_token:
                return {"Authorization": f"Bearer {communicator.config.open_access_token}"}
        return {}

    @staticmethod
    def _build_url(endpoint: Endpoint, request: PylonRequest) -> str:
        if isinstance(request, AuthenticatedPylonRequest):
            return endpoint.absolute_url(
                netuid_=request.netuid,
                identity_name_=request.identity_name,
                **request.model_dump(exclude={"netuid", "identity_name"}),
            )
        return endpoint.absolute_url(is_public_=True, **request.model_dump())

    def _translate_get_neurons(self, request: GetNeuronsRequest, communicator: HttpCommunicatorT) -> Request:
        url = self._build_url(self._endpoint_cls.NEURONS, request)
        headers = self._get_auth_headers(request, communicator)
        return communicator.raw_client.build_request(method=self._endpoint_cls.NEURONS.method, url=url, headers=headers)

    def _translate_get_latest_neurons(
        self, request: GetLatestNeuronsRequest, communicator: HttpCommunicatorT
    ) -> Request:
        url = self._build_url(self._endpoint_cls.LATEST_NEURONS, request)
        headers = self._get_auth_headers(request, communicator)
        return communicator.raw_client.build_request(
            method=self._endpoint_cls.LATEST_NEURONS.method, url=url, headers=headers
        )

    def _translate_get_recent_neurons(
        self, request: GetRecentNeuronsRequest, communicator: HttpCommunicatorT
    ) -> Request:
        url = self._build_url(self._endpoint_cls.RECENT_NEURONS, request)
        headers = self._get_auth_headers(request, communicator)
        return communicator.raw_client.build_request(
            method=self._endpoint_cls.RECENT_NEURONS.method, url=url, headers=headers
        )

    def _translate_get_validators(self, request: GetValidatorsRequest, communicator: HttpCommunicatorT) -> Request:
        url = self._build_url(self._endpoint_cls.VALIDATORS, request)
        headers = self._get_auth_headers(request, communicator)
        return communicator.raw_client.build_request(
            method=self._endpoint_cls.VALIDATORS.method, url=url, headers=headers
        )

    def _translate_get_latest_validators(
        self, request: GetLatestValidatorsRequest, communicator: HttpCommunicatorT
    ) -> Request:
        url = self._build_url(self._endpoint_cls.LATEST_VALIDATORS, request)
        headers = self._get_auth_headers(request, communicator)
        return communicator.raw_client.build_request(
            method=self._endpoint_cls.LATEST_VALIDATORS.method, url=url, headers=headers
        )

    def _translate_get_commitments(self, request: GetCommitmentsRequest, communicator: HttpCommunicatorT) -> Request:
        url = self._build_url(self._endpoint_cls.LATEST_COMMITMENTS, request)
        headers = self._get_auth_headers(request, communicator)
        return communicator.raw_client.build_request(
            method=self._endpoint_cls.LATEST_COMMITMENTS.method, url=url, headers=headers
        )

    def _translate_get_all_revealed_commitments(
        self, request: GetAllRevealedCommitmentsRequest, communicator: HttpCommunicatorT
    ) -> Request:
        url = self._build_url(self._endpoint_cls.LATEST_COMMITMENTS_REVEALED, request)
        headers = self._get_auth_headers(request, communicator)
        return communicator.raw_client.build_request(
            method=self._endpoint_cls.LATEST_COMMITMENTS_REVEALED.method, url=url, headers=headers
        )

    def _translate_get_commitment(self, request: GetCommitmentRequest, communicator: HttpCommunicatorT) -> Request:
        url = self._build_url(self._endpoint_cls.LATEST_COMMITMENTS_HOTKEY, request)
        headers = self._get_auth_headers(request, communicator)
        return communicator.raw_client.build_request(
            method=self._endpoint_cls.LATEST_COMMITMENTS_HOTKEY.method, url=url, headers=headers
        )

    def _translate_get_revealed_commitments(
        self, request: GetRevealedCommitmentsRequest, communicator: HttpCommunicatorT
    ) -> Request:
        url = self._build_url(self._endpoint_cls.LATEST_COMMITMENTS_REVEALED_HOTKEY, request)
        headers = self._get_auth_headers(request, communicator)
        return communicator.raw_client.build_request(
            method=self._endpoint_cls.LATEST_COMMITMENTS_REVEALED_HOTKEY.method, url=url, headers=headers
        )

    def _translate_get_own_commitment(
        self, request: GetOwnCommitmentRequest, communicator: HttpCommunicatorT
    ) -> Request:
        url = self._build_url(self._endpoint_cls.LATEST_COMMITMENTS_SELF, request)
        headers = self._get_auth_headers(request, communicator)
        return communicator.raw_client.build_request(
            method=self._endpoint_cls.LATEST_COMMITMENTS_SELF.method, url=url, headers=headers
        )

    def _translate_get_own_revealed_commitments(
        self, request: GetOwnRevealedCommitmentsRequest, communicator: HttpCommunicatorT
    ) -> Request:
        url = self._build_url(self._endpoint_cls.LATEST_COMMITMENTS_REVEALED_SELF, request)
        headers = self._get_auth_headers(request, communicator)
        return communicator.raw_client.build_request(
            method=self._endpoint_cls.LATEST_COMMITMENTS_REVEALED_SELF.method, url=url, headers=headers
        )

    def _translate_set_weights(self, request: SetWeightsRequest, communicator: HttpCommunicatorT) -> Request:
        url = self._build_url(self._endpoint_cls.SUBNET_MECHANISM_WEIGHTS, request)
        headers = self._get_auth_headers(request, communicator)
        return communicator.raw_client.build_request(
            method=self._endpoint_cls.SUBNET_MECHANISM_WEIGHTS.method,
            url=url,
            headers=headers,
            json=request.model_dump(include={"weights"}),
        )

    def _translate_get_weights_status(
        self, request: GetWeightsStatusRequest, communicator: HttpCommunicatorT
    ) -> Request:
        url = self._build_url(self._endpoint_cls.SUBNET_MECHANISM_WEIGHTS_STATUS, request)
        headers = self._get_auth_headers(request, communicator)
        return communicator.raw_client.build_request(
            method=self._endpoint_cls.SUBNET_MECHANISM_WEIGHTS_STATUS.method,
            url=url,
            headers=headers,
        )

    def _translate_set_commitment(self, request: SetCommitmentRequest, communicator: HttpCommunicatorT) -> Request:
        url = self._build_url(self._endpoint_cls.COMMITMENTS, request)
        headers = self._get_auth_headers(request, communicator)
        return communicator.raw_client.build_request(
            method=self._endpoint_cls.COMMITMENTS.method,
            url=url,
            headers=headers,
            json=request.model_dump(include={"commitment"}),
        )

    def _translate_set_revealed_commitment(
        self, request: SetRevealedCommitmentRequest, communicator: HttpCommunicatorT
    ) -> Request:
        url = self._build_url(self._endpoint_cls.REVEALED_COMMITMENTS, request)
        headers = self._get_auth_headers(request, communicator)
        return communicator.raw_client.build_request(
            method=self._endpoint_cls.REVEALED_COMMITMENTS.method,
            url=url,
            headers=headers,
            json=request.model_dump(include={"commitment", "blocks_until_reveal"}),
        )

    def _translate_get_identities(self, request: GetIdentitiesRequest, communicator: HttpCommunicatorT) -> Request:
        url = self._build_url(self._endpoint_cls.IDENTITIES, request)
        headers = self._get_auth_headers(request, communicator)
        return communicator.raw_client.build_request(
            method=self._endpoint_cls.IDENTITIES.method, url=url, headers=headers
        )

    def _translate_get_latest_block_info(
        self, request: GetLatestBlockInfoRequest, communicator: HttpCommunicatorT
    ) -> Request:
        url = self._build_url(self._endpoint_cls.LATEST_BLOCK_INFO, request)
        headers = self._get_auth_headers(request, communicator)
        return communicator.raw_client.build_request(
            method=self._endpoint_cls.LATEST_BLOCK_INFO.method, url=url, headers=headers
        )

    def _translate_get_latest_prices(self, request: GetLatestPricesRequest, communicator: HttpCommunicatorT) -> Request:
        url = self._build_url(self._endpoint_cls.LATEST_PRICES, request)
        headers = self._get_auth_headers(request, communicator)
        return communicator.raw_client.build_request(
            method=self._endpoint_cls.LATEST_PRICES.method, url=url, headers=headers
        )

    def _translate_get_prices(self, request: GetPricesRequest, communicator: HttpCommunicatorT) -> Request:
        url = self._build_url(self._endpoint_cls.PRICES, request)
        headers = self._get_auth_headers(request, communicator)
        return communicator.raw_client.build_request(method=self._endpoint_cls.PRICES.method, url=url, headers=headers)

    def _translate_get_latest_price(self, request: GetLatestPriceRequest, communicator: HttpCommunicatorT) -> Request:
        url = self._build_url(self._endpoint_cls.SUBNET_LATEST_PRICE, request)
        headers = self._get_auth_headers(request, communicator)
        return communicator.raw_client.build_request(
            method=self._endpoint_cls.SUBNET_LATEST_PRICE.method, url=url, headers=headers
        )

    def _translate_get_price(self, request: GetPriceRequest, communicator: HttpCommunicatorT) -> Request:
        url = self._build_url(self._endpoint_cls.SUBNET_PRICE, request)
        headers = self._get_auth_headers(request, communicator)
        return communicator.raw_client.build_request(
            method=self._endpoint_cls.SUBNET_PRICE.method, url=url, headers=headers
        )

    def _translate_get_extrinsic(self, request: GetExtrinsicRequest, communicator: HttpCommunicatorT) -> Request:
        url = self._build_url(self._endpoint_cls.EXTRINSIC, request)
        headers = self._get_auth_headers(request, communicator)
        return communicator.raw_client.build_request(
            method=self._endpoint_cls.EXTRINSIC.method, url=url, headers=headers
        )

    def _translate_get_drand_last_stored_round(
        self, request: GetDrandLastStoredRoundRequest, communicator: HttpCommunicatorT
    ) -> Request:
        url = self._build_url(self._endpoint_cls.DRAND_LAST_STORED_ROUND, request)
        return communicator.raw_client.build_request(method=self._endpoint_cls.DRAND_LAST_STORED_ROUND.method, url=url)

    def _translate_get_latest_evm_associations(
        self, request: GetLatestEvmAssociationsRequest, communicator: HttpCommunicatorT
    ) -> Request:
        url = self._build_url(self._endpoint_cls.LATEST_EVM_ASSOCIATIONS, request)
        headers = self._get_auth_headers(request, communicator)
        return communicator.raw_client.build_request(
            method=self._endpoint_cls.LATEST_EVM_ASSOCIATIONS.method, url=url, headers=headers
        )

    def _translate_get_evm_logs(self, request: GetEvmLogsRequest, communicator: HttpCommunicatorT) -> Request:
        url = self._endpoint_cls.EVM_LOGS.absolute_url(contract_address=request.contract_address)
        headers = self._get_auth_headers(request, communicator)
        return communicator.raw_client.build_request(
            method=self._endpoint_cls.EVM_LOGS.method,
            url=url,
            headers=headers,
            params={"from_block": request.from_block, "to_block": request.to_block},
            json=request.model_dump(include={"abi"}),
        )
