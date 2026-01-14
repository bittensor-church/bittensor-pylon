import asyncio
import inspect
from collections import defaultdict
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any, TypeAlias

Behavior: TypeAlias = Callable | Exception | Any
MethodName: TypeAlias = str
Call: TypeAlias = tuple


class Behave:
    """
    A reusable behavior mocker that 'behaves' in the configured way when called.
    It can be used to create mock implementations from abstract classes for testing.
    The behavior can be verified through recorded calls and tests.

    Example usage:
        One can add an instance of this class to a concrete implementation class, and record
        calls act according to configured behaviors.
        class MockConcreteClass(AbstractClass):
            def __init__(self):
                self.behave = Behave()

            def method_to_mock(self, arg1, arg2):
                self.behave.track("method_to_mock", arg1, arg2)
                return self.behave.execute("method_to_mock", arg1, arg2)

        # In the test:
        mock_instance = MockConcreteClass()

        async with mock_instance.behave.mock(method_to_mock=[1, Exception("Error")]):
            assert mock_instance.method_to_mock("A", "B") == 1
            with pytest.raises(Exception, match="Error"):
                mock_instance.method_to_mock("C", "D")

        assert mock_instance.behave.calls["method_to_mock"] == [("A", "B"), ("C", "D")]
    """

    def __init__(self) -> None:
        """Initialize the behavior engine."""
        self._lock = asyncio.Lock()
        self._behaviors: dict[MethodName, list[Behavior]] = defaultdict(list)
        self.calls: dict[MethodName, list[Call]] = defaultdict(list)

    @asynccontextmanager
    async def mock(self, **behaviors: list[Behavior] | Behavior):
        """
        Context manager to configure mock behavior for methods.

        Args:
            **behaviors: Method names as keys, and either:
                - A list of behaviors (each can be a callable, value, or exception)
                - A single behavior (callable, value, or exception)

        Each behavior can be:
            - A callable that will be called with the method's arguments
            - A value to be returned directly
            - An exception instance to be raised

        Example:
            async with behave.mock(
                get_latest_block=[Block(number=100, hash=BlockHash("0x123"))],
                get_certificates=[
                    lambda netuid, block: {...},
                    {"hotkey": NeuronCertificate(...)},
                ],
                get_certificate=[None, Exception("Network error")]
            ):
                # Test code here
        """
        for method_name, behavior in behaviors.items():
            if not isinstance(behavior, list):
                self._behaviors[method_name].append(behavior)
            else:
                self._behaviors[method_name].extend(behavior)

        try:
            yield
        finally:
            self._behaviors.clear()

    async def execute(self, method_name: str, *args, **kwargs) -> Any:
        """
        Execute the next configured behavior for a method.

        Args:
            method_name: Name of the method
            *args: Positional arguments passed to the method
            **kwargs: Keyword arguments passed to the method

        Returns:
            The result of the configured behavior
        """
        async with self._lock:
            if not self._behaviors[method_name]:
                raise NotImplementedError(
                    f"No mock behavior configured for {method_name}. "
                    f"Use mock_behavior() context manager to configure it."
                )

            # Get the next behavior from the queue (FIFO)
            behavior = self._behaviors[method_name].pop(0)

        if isinstance(behavior, Exception):
            raise behavior

        if callable(behavior):
            result = behavior(*args, **kwargs)
            # If the result is awaitable (coroutine), await it
            if inspect.iscoroutine(result):
                return await result

            return result

        return behavior

    def track(self, method_name: str, *args, **kwargs) -> None:
        """
        Track a method call for later assertion.

        Args:
            method_name: Name of the method being called
            *args: Positional arguments passed to the method
            **kwargs: Keyword arguments passed to the method
        """
        if kwargs:
            self.calls[method_name].append((args, kwargs))
        else:
            self.calls[method_name].append(args)

    def reset(self) -> None:
        """
        Reset all call tracking and behaviors.
        """
        self.calls.clear()
        self._behaviors.clear()
