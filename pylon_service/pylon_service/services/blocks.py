from pylon_commons.models import BlockInfoBag
from pylon_commons.types import BlockNumber, ExtrinsicIndex

from pylon_service.bittensor.contact import BittensorPort
from pylon_service.bittensor.models import Block, Extrinsic

from .errors import BlockNotFoundError, ExtrinsicNotFoundError


class BlockService:
    async def get_existing_block(self, router: BittensorPort, block_number: BlockNumber) -> Block:
        block = await router.get_block(block_number)
        if block is None:
            raise BlockNotFoundError(f"Block {block_number} not found.")
        return block

    async def get_latest_block_info(self, router: BittensorPort) -> BlockInfoBag:
        block = await router.get_latest_block()
        timestamp = await router.get_block_timestamp(block)
        return BlockInfoBag(number=block.number, hash=block.hash, timestamp=timestamp)

    async def get_extrinsic(
        self, router: BittensorPort, block_number: BlockNumber, extrinsic_index: ExtrinsicIndex
    ) -> Extrinsic:
        block = await self.get_existing_block(router, block_number)
        extrinsic = await router.get_extrinsic(block, extrinsic_index)
        if extrinsic is None:
            raise ExtrinsicNotFoundError(f"Extrinsic {block_number}-{extrinsic_index} not found.")
        return extrinsic
