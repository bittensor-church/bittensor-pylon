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
    Error that pylon client issues on receiving an error response from Pylon.
    """

    def __init__(self, message: str, status_code: int | None = None, detail: str | None = None):
        self.status_code = status_code
        self.detail = detail
        if status_code is not None:
            message = f"{message} (HTTP {status_code})"
        if detail:
            message = f"{message}: {detail}"
        super().__init__(message)


class PylonUnauthorized(PylonResponseException):
    """
    Error raised when the request to Pylon failed due to unauthorized access.
    """

    def __init__(self, detail: str | None = None):
        super().__init__("Unauthorized", status_code=401, detail=detail)


class PylonForbidden(PylonResponseException):
    """
    Error raised when the request to Pylon failed due to lack of permissions.
    """

    def __init__(self, detail: str | None = None):
        super().__init__("Forbidden", status_code=403, detail=detail)


class PylonNotFound(PylonResponseException):
    """
    Error raised when the requested resource was not found.
    """

    def __init__(self, detail: str | None = None):
        super().__init__("Not found", status_code=404, detail=detail)


class PylonClosed(BasePylonException):
    """
    Error raised when attempting to use a client that has not been opened.
    """


class PylonMisconfigured(BasePylonException):
    """
    Error raised when client configuration is invalid or incomplete.
    """
