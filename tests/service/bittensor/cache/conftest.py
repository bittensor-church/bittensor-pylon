import random

import pytest

from pylon._internal.common.models import Block, SubnetNeurons
from pylon._internal.common.types import Timestamp
from tests.factories import BlockFactory, NeuronFactory


@pytest.fixture
def recent_neurons_factory(block_factory: BlockFactory, neuron_factory: NeuronFactory):
    def factory() -> tuple[Timestamp, Block, SubnetNeurons]:
        block = block_factory.build()
        neurons = {n.hotkey: n for n in neuron_factory.batch(3)}
        return Timestamp(random.randint(123456, 234567)), block, SubnetNeurons(block=block, neurons=neurons)

    return factory
