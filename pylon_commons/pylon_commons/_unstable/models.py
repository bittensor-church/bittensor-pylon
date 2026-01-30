from ..models import BittensorModel, Block, Commitment
from ..types import Hotkey


class SubnetCommitments(BittensorModel):
    block: Block
    commitments: dict[Hotkey, Commitment]
