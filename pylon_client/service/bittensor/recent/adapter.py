import logging
from typing import Generic, Self, TypeVar

from litestar.stores.base import Store
from pydantic import BaseModel, ValidationError

from pylon_client._internal.common.models import BittensorModel
from pylon_client._internal.common.types import HotkeyName, NetUid, Timestamp

logger = logging.getLogger(__name__)

ModelT = TypeVar("ModelT", bound=BittensorModel)


class CacheKey(str, Generic[ModelT]):
    """
    A string subclass to represent a cache key for recent data. A model-class name,
    an optional netuid and an optional hotkey are combined to uniquely identify
    a cache entry.
    """

    def __new__(cls, model: type[ModelT], netuid: NetUid | None, hotkey_name: HotkeyName | None) -> Self:
        key = f"recent_{model.__name__}_{netuid}_{hotkey_name}"
        return super().__new__(cls, key)  # type: ignore


class _CacheEntry(BaseModel):
    """
    This class is internal to this module. It is used to serialize/deserialize cache entries via pydantic.
    """

    data: str
    timestamp: Timestamp


class RecentCacheAdapter(Generic[ModelT]):
    """
    A generic cache adapter on top of the litestar store. This class:
        - Serializes/deserializes cache entries to/from JSON via pydantic.
        - Stores cache entries in the litestar store.
        - Validates cache entries against the model class.
    """

    def __init__(
        self,
        key: CacheKey[ModelT],
        store: Store,
        model: type[ModelT],
    ) -> None:
        """
        Args:
            key: CacheKey to get and store the cache entry under.
            store: Litestar store instance.
            model: BittensorModel class. In the context of this class,
                the model is used as a serializer and validator.
        """
        self._key = key
        self._model = model
        self._store = store

    async def save(self, timestamp: Timestamp, object_: ModelT) -> None:
        """
        Saves a cache entry in the wrapped store.
        Args:
            timestamp: timestamp of the block this data is associated with.
            object_: The object to be cached.
        """
        data = object_.model_dump_json()
        entry = _CacheEntry(data=data, timestamp=timestamp).model_dump_json()
        await self._store.set(self._key, entry)

    async def get(self) -> tuple[Timestamp, ModelT] | None:
        """
        Gets a cache entry from the store backend.
        """
        data = await self._store.get(self._key)
        if data is None:
            return None

        try:
            entry = _CacheEntry.model_validate_json(data)
            object_ = self._model.model_validate_json(entry.data)
        except ValidationError:
            logger.warning("Cache entry validation failed. Deleting invalid entry.")
            await self._store.delete(self._key)
            return None

        return entry.timestamp, object_
