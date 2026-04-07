from pylon_commons.types import CommitmentDataBytes, NetUid

from pylon_service.bittensor.contact import BittensorPort
from pylon_service.bittensor.models import Block, Commitment, SubnetCommitments

from .errors import CommitmentNotFoundError


class CommitmentService:
    async def get_commitments(self, router: BittensorPort, netuid: NetUid, block: Block) -> SubnetCommitments:
        commitments = await router.get_commitments(netuid, block)
        state = await router.get_subnet_state(netuid, block)
        registered_hotkeys = set(state.hotkeys)
        filtered = {
            hotkey: commitment for hotkey, commitment in commitments.commitments.items() if hotkey in registered_hotkeys
        }
        return SubnetCommitments(block=commitments.block, commitments=filtered)

    async def get_latest_commitments(self, router: BittensorPort, netuid: NetUid) -> SubnetCommitments:
        block = await router.get_latest_block()
        return await self.get_commitments(router, netuid, block)

    async def get_commitment(self, router: BittensorPort, netuid: NetUid, hotkey) -> tuple[Block, Commitment]:
        block = await router.get_latest_block()
        commitment = await router.get_commitment(netuid, block, hotkey=hotkey)
        if commitment is None:
            raise CommitmentNotFoundError("Commitment not found.")
        return block, commitment

    async def get_own_commitment(self, router: BittensorPort, netuid: NetUid) -> tuple[Block, Commitment]:
        block = await router.get_latest_block()
        commitment = await router.get_commitment(netuid, block)
        if commitment is None:
            raise CommitmentNotFoundError("Commitment not found.")
        return block, commitment

    async def set_commitment(self, router: BittensorPort, netuid: NetUid, data: CommitmentDataBytes) -> None:
        await router.set_commitment(netuid, data)
