from typing import ClassVar


class BasePylonException(Exception):
    """
    Base class for every pylon exception.
    """


class PylonRequestException(BasePylonException):
    """
    Error that pylon client issues when it fails to deliver the request to Pylon.
    """


class PylonResponseException(BasePylonException):
    """
    Error raised when Pylon returns an error response (4xx/5xx status code).
    """

    default_message: ClassVar[str] = "Pylon returned an error"
    default_status_code: ClassVar[int | None] = None

    def __init__(self, message: str | None = None, status_code: int | None = None, detail: str | None = None):
        self.status_code = status_code if status_code is not None else self.default_status_code
        self.detail = detail
        msg = message if message is not None else self.default_message
        if self.status_code is not None:
            msg = f"{msg} (HTTP {self.status_code})"
        if detail:
            msg = f"{msg}: {detail}"
        super().__init__(msg)


class PylonUnauthorized(PylonResponseException):
    """
    Error raised when the request to Pylon failed due to unauthorized access.
    """

    default_message: ClassVar[str] = "Unauthorized"
    default_status_code: ClassVar[int | None] = 401


class PylonForbidden(PylonResponseException):
    """
    Error raised when the request to Pylon failed due to lack of permissions.
    """

    default_message: ClassVar[str] = "Forbidden"
    default_status_code: ClassVar[int | None] = 403


class PylonNotFound(PylonResponseException):
    """
    Error raised when the requested resource was not found.
    """

    default_message: ClassVar[str] = "Not found"
    default_status_code: ClassVar[int | None] = 404


class PylonBadGateway(PylonResponseException):
    """
    Error raised when Pylon received an invalid response from the upstream Bittensor node.
    """

    default_message: ClassVar[str] = "Bad gateway"
    default_status_code: ClassVar[int | None] = 502


class PylonClosed(BasePylonException):
    """
    Error raised when attempting to use a client that has not been opened.
    """


class PylonMisconfigured(BasePylonException):
    """
    Error raised when client configuration is invalid or incomplete.
    """


class PylonCacheException(BasePylonException):
    """Base class for all Pylon cache exception."""
