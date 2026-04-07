"""
Compatibility shim for tests migrating from mock clients to mock contacts.

This remains the shared transport double for public-API tests, but it now supports defaults
so the shared-world fixture can define common state without consuming per-test behavior queues.
"""

from __future__ import annotations

import inspect
from typing import Any

from tests.behave import Behavior

from pylon_service.bittensor.contact import MockBittensorContact


class MockBittensorClient(MockBittensorContact):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.defaults: dict[str, Behavior] = {}

    def set_default(self, method_name: str, behavior: Behavior) -> None:
        self.defaults[method_name] = behavior

    def reset(self) -> None:
        super().reset()
        self.defaults.clear()

    async def _execute_behavior(self, method_name: str, *args, **kwargs) -> Any:
        self._behave.track(method_name, *args, **kwargs)
        try:
            return await self._behave.execute(method_name, *args, **kwargs)
        except NotImplementedError:
            if method_name not in self.defaults:
                raise

        behavior = self.defaults[method_name]
        if isinstance(behavior, Exception):
            raise behavior
        if callable(behavior):
            result = behavior(*args, **kwargs)
            if inspect.iscoroutine(result):
                return await result
            return result
        return behavior


__all__ = ["MockBittensorClient"]
