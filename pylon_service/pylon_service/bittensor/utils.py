from typing import cast

from pylon_commons.models import CommitmentVariant, HexDataCommitment, RevealedCommitment, TimelockEncryptedCommitment
from pylon_commons.types import BlockNumber, CommitmentDataBytes, Hotkey, RevealedCommitmentData
from turbobt import Commitment as TurboBtCommitment
from turbobt import RevealedCommitment as TurboBtRevealedCommitment


def map_to_commitment(raw_commitment: TurboBtCommitment, hotkey: Hotkey) -> CommitmentVariant:
    match raw_commitment["kind"]:
        case "timelock_encrypted":
            reveal_round = raw_commitment.get("reveal_round")
            if reveal_round is None:
                raise ValueError("reveal_round is missing for timelock_encrypted commitment")
            return TimelockEncryptedCommitment(
                commitment_block_number=BlockNumber(raw_commitment["block"]),
                hotkey=hotkey,
                commitment=CommitmentDataBytes(raw_commitment["data"]).hex(),
                reveal_round=cast(int, reveal_round),
            )
        case "hex_data":
            return HexDataCommitment(
                commitment_block_number=BlockNumber(raw_commitment["block"]),
                hotkey=hotkey,
                commitment=CommitmentDataBytes(raw_commitment["data"]).hex(),
            )
        case _:
            raise ValueError(f"Unknown commitment kind: {raw_commitment['kind']}")


def map_to_revealed_commitment(raw_commitment: TurboBtRevealedCommitment, hotkey: Hotkey) -> RevealedCommitment:
    return RevealedCommitment(
        reveal_block_number=BlockNumber(raw_commitment["reveal_block"]),
        hotkey=hotkey,
        commitment=RevealedCommitmentData(raw_commitment["data"]),
    )
