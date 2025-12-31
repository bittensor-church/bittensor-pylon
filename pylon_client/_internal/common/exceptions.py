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


class PylonUnauthorized(PylonResponseException):
    """
    Error raised when the request to Pylon failed due to unauthorized access.
    """


class PylonForbidden(PylonResponseException):
    """
    Error raised when the request to Pylon failed due to lack of permissions.
    """


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
