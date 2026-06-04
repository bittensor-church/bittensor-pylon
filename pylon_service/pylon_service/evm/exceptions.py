class EvmException(Exception):
    """
    Base exception for all EVM contact errors.
    """

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class EvmRpcError(EvmException):
    """
    Raised when the EVM RPC node returns an error response.
    """


class EvmInvalidAddressError(EvmException):
    """
    Raised when the provided contract address is not a valid EVM address.
    """


class EvmInvalidAbiError(EvmException):
    """
    Raised when the provided ABI is malformed or contains no valid event definitions.
    """
