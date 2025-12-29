"""
This module creates and manages a 'stores' dictionary for Litestar app.

Adding a new store:
- Add the store's name as a new 'StoreName' enum member.
- Add the store instance to the 'stores' dictionary against the name.
- Access the store from the litestar app using 'app.stores.get(StoreName.RECENT_OBJECTS)'
"""

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
