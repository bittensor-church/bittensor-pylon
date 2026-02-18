from __future__ import annotations

from typing import Generic, TypeVar

from pylon_client._internal.pylon_commons._unstable.requests import PylonRequest

RawRequestT = TypeVar("RawRequestT")
CommunicatorT = TypeVar("CommunicatorT")


class AbstractRequestTranslator(Generic[RawRequestT, CommunicatorT]):
    """
    Translates a PylonRequest into a raw request object for a specific API version.
    """

    def translate(self, request: PylonRequest, communicator: CommunicatorT) -> RawRequestT:
        handler_name = f"_translate_{request.request_type}"
        handler = getattr(self, handler_name, None)
        if handler is None:
            raise NotImplementedError(f"Request of type {type(request).__name__} is not supported.")
        return handler(request, communicator)
