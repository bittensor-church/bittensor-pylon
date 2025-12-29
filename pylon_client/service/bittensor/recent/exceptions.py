from pylon_client._internal.common.exceptions import PylonCacheException


class RecentObjectMissing(PylonCacheException):
    """
    Raised when a recent object is missing.
    """


class RecentObjectStale(PylonCacheException):
    """
    Raised when the recent object is stale (w.r.t hard limit).
    """
