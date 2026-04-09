from pylon_commons.models import BlockInfoBag
from pylon_commons.types import BlockNumber, ExtrinsicIndex

from pylon_service.bittensor.contact import BittensorPort
from pylon_service.bittensor.models import Block, Extrinsic

from .errors import BlockNotFoundError, ExtrinsicNotFoundError


class BlockService:
    async def get_existing_block(self, contact_router: BittensorPort, block_number: BlockNumber) -> Block:
        block = await contact_router.get_block(block_number)
        if block is None:
            raise BlockNotFoundError(f"Block {block_number} not found.")
        return block

    async def get_latest_block_info(self, contact_router: BittensorPort) -> BlockInfoBag:
        block = await contact_router.get_latest_block()
        timestamp = await contact_router.get_block_timestamp(block)
        return BlockInfoBag(number=block.number, hash=block.hash, timestamp=timestamp)

    async def get_extrinsic(
        self, contact_router: BittensorPort, block_number: BlockNumber, extrinsic_index: ExtrinsicIndex
    ) -> Extrinsic:
        block = await self.get_existing_block(contact_router, block_number)
        extrinsic = await contact_router.get_extrinsic(block, extrinsic_index)
        if extrinsic is None:
            raise ExtrinsicNotFoundError(f"Extrinsic {block_number}-{extrinsic_index} not found.")
        return extrinsic
