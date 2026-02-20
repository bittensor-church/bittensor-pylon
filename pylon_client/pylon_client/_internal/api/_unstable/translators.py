from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from httpx import Request

from pylon_client._internal.pylon_commons._unstable.endpoints import Endpoint as EndpointUnstable
from pylon_client._internal.pylon_commons._unstable.requests import (
    AuthenticatedPylonRequest,
    GetCommitmentRequest,
    GetCommitmentsRequest,
    GetExtrinsicRequest,
    GetLatestBlockInfoRequest,
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
    def _build_url(endpoint: Endpoint, request: PylonRequest) -> str:
        if isinstance(request, AuthenticatedPylonRequest):
            return endpoint.absolute_url(
                netuid_=request.netuid,
                identity_name_=request.identity_name,
                **request.model_dump(exclude={"netuid", "identity_name"}),
            )
        return endpoint.absolute_url(**request.model_dump())

    def _translate_get_neurons(self, request: GetNeuronsRequest, communicator: HttpCommunicatorT) -> Request:
        url = self._build_url(self._endpoint_cls.NEURONS, request)
        return communicator.raw_client.build_request(method=self._endpoint_cls.NEURONS.method, url=url)

    def _translate_get_latest_neurons(
        self, request: GetLatestNeuronsRequest, communicator: HttpCommunicatorT
    ) -> Request:
        url = self._build_url(self._endpoint_cls.LATEST_NEURONS, request)
        return communicator.raw_client.build_request(method=self._endpoint_cls.LATEST_NEURONS.method, url=url)

    def _translate_get_recent_neurons(
        self, request: GetRecentNeuronsRequest, communicator: HttpCommunicatorT
    ) -> Request:
        url = self._build_url(self._endpoint_cls.RECENT_NEURONS, request)
        return communicator.raw_client.build_request(method=self._endpoint_cls.RECENT_NEURONS.method, url=url)

    def _translate_get_validators(self, request: GetValidatorsRequest, communicator: HttpCommunicatorT) -> Request:
        url = self._build_url(self._endpoint_cls.VALIDATORS, request)
        return communicator.raw_client.build_request(method=self._endpoint_cls.VALIDATORS.method, url=url)

    def _translate_get_latest_validators(
        self, request: GetLatestValidatorsRequest, communicator: HttpCommunicatorT
    ) -> Request:
        url = self._build_url(self._endpoint_cls.LATEST_VALIDATORS, request)
        return communicator.raw_client.build_request(method=self._endpoint_cls.LATEST_VALIDATORS.method, url=url)

    def _translate_get_commitments(self, request: GetCommitmentsRequest, communicator: HttpCommunicatorT) -> Request:
        url = self._build_url(self._endpoint_cls.LATEST_COMMITMENTS, request)
        return communicator.raw_client.build_request(method=self._endpoint_cls.LATEST_COMMITMENTS.method, url=url)

    def _translate_get_commitment(self, request: GetCommitmentRequest, communicator: HttpCommunicatorT) -> Request:
        url = self._build_url(self._endpoint_cls.LATEST_COMMITMENTS_HOTKEY, request)
        return communicator.raw_client.build_request(
            method=self._endpoint_cls.LATEST_COMMITMENTS_HOTKEY.method, url=url
        )

    def _translate_get_own_commitment(
        self, request: GetOwnCommitmentRequest, communicator: HttpCommunicatorT
    ) -> Request:
        url = self._build_url(self._endpoint_cls.LATEST_COMMITMENTS_SELF, request)
        return communicator.raw_client.build_request(method=self._endpoint_cls.LATEST_COMMITMENTS_SELF.method, url=url)

    def _translate_set_weights(self, request: SetWeightsRequest, communicator: HttpCommunicatorT) -> Request:
        url = self._build_url(self._endpoint_cls.SUBNET_WEIGHTS, request)
        return communicator.raw_client.build_request(
            method=self._endpoint_cls.SUBNET_WEIGHTS.method,
            url=url,
            json=request.model_dump(include={"weights"}),
        )

    def _translate_set_commitment(self, request: SetCommitmentRequest, communicator: HttpCommunicatorT) -> Request:
        url = self._build_url(self._endpoint_cls.COMMITMENTS, request)
        return communicator.raw_client.build_request(
            method=self._endpoint_cls.COMMITMENTS.method,
            url=url,
            json=request.model_dump(include={"commitment"}),
        )

    def _translate_identity_login(self, request: IdentityLoginRequest, communicator: HttpCommunicatorT) -> Request:
        url = self._build_url(self._endpoint_cls.IDENTITY_LOGIN, request)
        return communicator.raw_client.build_request(
            method=self._endpoint_cls.IDENTITY_LOGIN.method, url=url, json=request.model_dump()
        )

    def _translate_get_latest_block_info(
        self, request: GetLatestBlockInfoRequest, communicator: HttpCommunicatorT
    ) -> Request:
        url = self._build_url(self._endpoint_cls.LATEST_BLOCK_INFO, request)
        return communicator.raw_client.build_request(method=self._endpoint_cls.LATEST_BLOCK_INFO.method, url=url)

    def _translate_get_extrinsic(self, request: GetExtrinsicRequest, communicator: HttpCommunicatorT) -> Request:
        url = self._build_url(self._endpoint_cls.EXTRINSIC, request)
        return communicator.raw_client.build_request(method=self._endpoint_cls.EXTRINSIC.method, url=url)
