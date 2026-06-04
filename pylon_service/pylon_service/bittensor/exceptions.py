class BittensorException(Exception):
    """
    Base exception for all bittensor client errors.
    """

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class BittensorTransportError(BittensorException):
    """
    Raised when a contact operation still fails after transport recovery.
    """

    def __init__(self, *, operation: str, uri: str, original_exception: BaseException):
        self.operation = operation
        self.uri = uri
        self.original_exception = original_exception
        self.error_type = type(original_exception).__name__
        message = str(original_exception).strip()
        self.transport_gist = f"{self.error_type}: {message}" if message else self.error_type
        super().__init__(f"{operation} failed on {uri}: {self.transport_gist}")


class ArchiveFallbackException(BittensorException):
    """
    Raised when block data is unavailable after archive node fallback.
    """


class ArchiveInvalidParamsException(ArchiveFallbackException):
    """
    Raised when the archive node returns 'Invalid params', possibly because it does not support named keyword arguments.
    """


class SubnetStateUnavailable(BittensorException):
    """
    Raised when subnet state is not available for a given netuid and block.
    """
