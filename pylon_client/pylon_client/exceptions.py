from pylon_client._internal.pylon_commons.exceptions import BasePylonException


class MtlsVerificationError(BasePylonException):
    """Raised when mTLS verification fails connecting to a miner."""
