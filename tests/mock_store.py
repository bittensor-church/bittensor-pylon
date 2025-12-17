from datetime import timedelta

from litestar.stores.base import Store

from tests.behave import Behave


class MockStore(Store):
    """
    A mock implementation of litestar.stores.base.Store for testing.
    """

    def __init__(self, behave: Behave) -> None:
        self._behave = behave

    async def set(self, key: str, value: str | bytes, expires_in: int | timedelta | None = None) -> None:
        self._behave.track("set", key, value, expires_in)
        return await self._behave.execute("set", key, value, expires_in)

    async def get(self, key: str, renew_for: int | timedelta | None = None) -> bytes | None:
        self._behave.track("get", key, renew_for)
        return await self._behave.execute("get", key, renew_for)

    async def delete(self, key: str) -> None:
        self._behave.track("delete", key)
        return await self._behave.execute("delete", key)

    async def delete_all(self) -> None:
        self._behave.track("delete_all")
        return await self._behave.execute("delete_all")

    async def exists(self, key: str) -> bool:
        self._behave.track("exists", key)
        return await self._behave.execute("exists", key)

    async def expires_in(self, key: str) -> int | None:
        self._behave.track("expires_in", key)
        return await self._behave.execute("expires_in", key)
