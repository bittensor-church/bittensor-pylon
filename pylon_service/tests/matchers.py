from __future__ import annotations

from typing import Any

from dirty_equals import IsInt, IsStr
from pydantic import BaseModel
from sqlalchemy import inspect

from pylon_service.db.database import Base

HASH_REGEX = r"^0x[0-9a-fA-F]{64}$"

SNAPSHOT_BLOCK = {
    "number": IsInt(ge=0),
    "hash": IsStr(regex=HASH_REGEX),
}


def db_row_model_dump(model: Base, *, exclude: set[str] | None = None):
    exclude = exclude or set()
    return {
        column.key: getattr(model, column.key) for column in inspect(type(model)).columns if column.key not in exclude
    }


def dict_model_dump(value: dict[Any, BaseModel]):
    return {key: value.model_dump() for key, value in value.items()}
