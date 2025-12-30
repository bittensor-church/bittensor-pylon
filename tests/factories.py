from collections.abc import Callable
from typing import Any, Generic, cast

from polyfactory.factories.pydantic_factory import ModelFactory, T

from pylon_client._internal.common.currency import Currency, Token
from pylon_client._internal.common.models import Block, Neuron


class PylonModelFactory(Generic[T], ModelFactory[T]):
    __is_base_factory__ = True

    @classmethod
    def get_provider_map(cls) -> dict[Any, Callable[[], Any]]:
        providers = super().get_provider_map()
        float_factory = cast(Callable[..., float], providers[float])
        return {
            **providers,
            Currency: lambda: Currency(float_factory(min_value=0)),
            Currency[Token.ALPHA]: lambda: Currency[Token.ALPHA](float_factory(min_value=0)),
            Currency[Token.TAO]: lambda: Currency[Token.TAO](float_factory(min_value=0)),
        }


class BlockFactory(PylonModelFactory[Block]):
    __check_model__ = True


class NeuronFactory(PylonModelFactory[Neuron]):
    __check_model__ = True
