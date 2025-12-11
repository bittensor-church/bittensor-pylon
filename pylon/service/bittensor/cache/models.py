from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

from pylon._internal.common.models import BittensorModel, Block
from pylon._internal.common.types import Timestamp

T = TypeVar("T", bound=BittensorModel)


class CacheEntry(BaseModel, Generic[T]):
    entry: T
    block: Block
    cached_at: Timestamp
