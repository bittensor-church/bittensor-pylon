from httpx import Request

from pylon_client._internal.api._unstable.translators import HttpCommunicatorT
from pylon_client._internal.api._unstable.translators import HttpTranslator as NewHttpTranslator
from pylon_client._internal.pylon_commons.v1.endpoints import Endpoint
from pylon_client._internal.pylon_commons.v1.requests import SetWeightsRequest


class HttpTranslator(NewHttpTranslator):
    """
    Translates PylonRequests into httpx Requests using v1 API endpoints.
    """

    _endpoint_cls = Endpoint

    def _translate_set_weights(self, request: SetWeightsRequest, communicator: HttpCommunicatorT) -> Request:  # type: ignore[reportIncompatibleMethodOverride]
        url = self._build_url(self._endpoint_cls.SUBNET_WEIGHTS, request)
        headers = self._get_auth_headers(request, communicator)
        return communicator.raw_client.build_request(
            method=self._endpoint_cls.SUBNET_WEIGHTS.method,
            url=url,
            headers=headers,
            json=request.model_dump(include={"weights"}),
        )
