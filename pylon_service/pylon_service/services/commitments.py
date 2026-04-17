from pylon_commons.models import CommitmentVariant, RevealedCommitment, SubnetRevealedCommitments
from pylon_commons.types import CommitmentDataBytes, Hotkey, NetUid, RevealedCommitmentData

from pylon_service.bittensor.contact import BittensorPort
from pylon_service.bittensor.models import Block, SubnetCommitments

from .errors import CommitmentNotFoundError


class CommitmentService:
    async def get_commitments(self, contact_router: BittensorPort, netuid: NetUid, block: Block) -> SubnetCommitments:
        commitments = await contact_router.get_commitments(netuid, block)
        state = await contact_router.get_subnet_state(netuid, block)
        if state is None:
            raise RuntimeError(f"Subnet state is unavailable for netuid {netuid} at block {block.number}.")
        registered_hotkeys = set(state.hotkeys)
        filtered = {
            hotkey: commitment for hotkey, commitment in commitments.commitments.items() if hotkey in registered_hotkeys
        }
        return SubnetCommitments(block=commitments.block, commitments=filtered)

    async def get_latest_commitments(self, contact_router: BittensorPort, netuid: NetUid) -> SubnetCommitments:
        block = await contact_router.get_latest_block()
        return await self.get_commitments(contact_router, netuid, block)

    async def get_commitment(
        self, contact_router: BittensorPort, netuid: NetUid, hotkey: Hotkey
    ) -> tuple[Block, CommitmentVariant]:
        block = await contact_router.get_latest_block()
        commitment = await contact_router.get_commitment(netuid, block, hotkey=hotkey)
        if commitment is None:
            raise CommitmentNotFoundError("Commitment not found.")
        return block, commitment

    async def get_own_commitment(
        self, contact_router: BittensorPort, netuid: NetUid
    ) -> tuple[Block, CommitmentVariant]:
        block = await contact_router.get_latest_block()
        commitment = await contact_router.get_commitment(netuid, block)
        if commitment is None:
            raise CommitmentNotFoundError("Commitment not found.")
        return block, commitment

    async def set_commitment(self, contact_router: BittensorPort, netuid: NetUid, data: CommitmentDataBytes) -> None:
        await contact_router.set_commitment(netuid, data)

    async def get_all_revealed_commitments(
        self, contact_router: BittensorPort, netuid: NetUid
    ) -> tuple[Block, SubnetRevealedCommitments]:
        block = await contact_router.get_latest_block()
        commitments = await contact_router.get_all_revealed_commitments(netuid, block)
        return block, commitments

    async def get_revealed_commitments(
        self, contact_router: BittensorPort, netuid: NetUid, hotkey: Hotkey | None = None
    ) -> tuple[Block, list[RevealedCommitment]]:
        block = await contact_router.get_latest_block()
        commitments = await contact_router.get_revealed_commitments(netuid, block, hotkey=hotkey)
        if commitments is None:
            raise CommitmentNotFoundError("Revealed commitments not found.")
        return block, commitments

    async def get_own_revealed_commitments(
        self, contact_router: BittensorPort, netuid: NetUid
    ) -> tuple[Block, list[RevealedCommitment]]:
        block = await contact_router.get_latest_block()
        commitments = await contact_router.get_revealed_commitments(netuid, block)
        if commitments is None:
            raise CommitmentNotFoundError("Revealed commitments not found.")
        return block, commitments

    async def set_revealed_commitment(
        self, contact_router: BittensorPort, netuid: NetUid, commitment: RevealedCommitmentData, block_to_reveal: int
    ) -> int:
        return await contact_router.set_revealed_commitment(netuid, commitment, block_to_reveal)
