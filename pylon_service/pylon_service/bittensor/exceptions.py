class BittensorException(Exception):
    """
    Base exception for all bittensor client errors.
    """

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class ArchiveFallbackException(BittensorException):
    """
    Raised when block data is unavailable after archive node fallback.
    """
