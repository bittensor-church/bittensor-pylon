from pylon_client._internal.api._unstable.translators import HttpTranslator as NewHttpTranslator
from pylon_client._internal.pylon_commons.v1.endpoints import Endpoint


class HttpTranslator(NewHttpTranslator):
    """
    Translates PylonRequests into httpx Requests using v1 API endpoints.
    """

    _endpoint_cls = Endpoint
