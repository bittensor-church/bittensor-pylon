from enum import StrEnum

from litestar.stores.base import Store
from litestar.stores.memory import MemoryStore


class StoreName(StrEnum):
    RECENT_OBJECTS = "recent_objects"


class _Stores(dict[str, Store]):
    """
    A specialized dictionary for managing stores.
    """

    def __init__(self) -> None:
        super().__init__()
        self[StoreName.RECENT_OBJECTS] = MemoryStore()


stores = _Stores()
