# pyright: reportWildcardImportFromLibrary=false
from pylon_commons._unstable.models import *  # noqa: F403
from pylon_commons.types import BlockNumber, EvmAddress

# Contact models intentionally start as pass-through exports of the latest canonical models.
# This module is the seam where contact-only fields may be added later without forcing DTO shape.


class RawEvmKeyAssociationInfo(BittensorModel):  # noqa: F405
    """
    Represents attributes of an EVM key association for a neuron retrieved from contact.
    """

    evm_address: EvmAddress
    last_block_where_ownership_was_proven: BlockNumber
