from pylon_commons.models import BittensorModel, Block, Commitment
from pylon_commons.types import Hotkey


class SubnetCommitments(BittensorModel):
    block: Block
    commitments: dict[Hotkey, Commitment]
