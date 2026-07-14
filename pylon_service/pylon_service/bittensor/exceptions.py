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


class RuntimeApiUnavailableException(BittensorException):
    """
    Raised when a runtime API method is not exported at the requested block.

    Subtensor returns RPC error code 4003 both for a genuinely unknown/pruned block and for a runtime
    method that a later runtime upgrade introduced (e.g. SwapRuntimeApi.current_alpha_price_all does not
    exist before block ~7782857). turbobt surfaces both as UnknownBlock, so we disambiguate on the message
    and raise this instead of the misleading ArchiveFallbackException ("block data is unavailable").
    """


def is_missing_runtime_method(exc: BaseException) -> bool:
    """
    Detect Subtensor's "Exported method ... is not found" error.

    turbobt maps every RPC error with code 4003 to UnknownBlock, conflating a missing runtime method with
    a genuinely unknown block. The distinguishing signal is only in the message text.
    """
    message = str(exc)
    return "Exported method" in message and "is not found" in message
