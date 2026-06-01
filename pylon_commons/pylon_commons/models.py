from enum import IntEnum, StrEnum
from ipaddress import IPv4Address, IPv6Address
from typing import Annotated, Any, Generic, Literal, TypeAlias, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from .currency import Currency, Token
from .types import (
    AlphaPriceRao,
    AlphaStake,
    AlphaStakeRao,
    BlockHash,
    BlockNumber,
    Coldkey,
    CommitmentDataHex,
    Consensus,
    Dividends,
    Emission,
    EmissionRao,
    EvmAddress,
    ExtrinsicHash,
    ExtrinsicIndex,
    ExtrinsicLength,
    Hotkey,
    Incentive,
    MaxWeightsLimit,
    NetUid,
    NeuronActive,
    NeuronUid,
    Port,
    PrivateKey,
    PruningScore,
    PublicKey,
    Rank,
    RevealedCommitmentData,
    Stake,
    SubnetActive,
    TaoStake,
    TaoStakeRao,
    Tempo,
    Timestamp,
    TotalStake,
    TotalStakeRao,
    Trust,
    ValidatorPermit,
    ValidatorTrust,
)


class UnknownIntEnum(IntEnum):
    """
    Allows to use int enum with undefined values.
    """

    @classmethod
    def _missing_(cls, value):
        assert isinstance(value, int)
        member = int.__new__(cls, value)
        member._name_ = f"UNKNOWN_{value}"
        member._value_ = value
        return member


class CommitReveal(StrEnum):
    DISABLED = "disabled"
    V2 = "v2"
    V3 = "v3"
    V4 = "v4"


# Pydantic models


class BittensorModel(BaseModel):
    pass


class Block(BittensorModel):
    number: BlockNumber
    hash: BlockHash


class BlockInfoBag(Block):
    """
    Enriched block info used for the block info endpoint, so as not to bloat the Block struct.
    """

    timestamp: Timestamp


class AxonProtocol(UnknownIntEnum):
    TCP = 0
    UDP = 1
    HTTP = 4


class AxonInfo(BittensorModel):
    ip: IPv4Address | IPv6Address
    port: Port
    protocol: AxonProtocol

    @property
    def is_serving(self) -> bool:
        return self.ip not in (IPv4Address("0.0.0.0"), IPv6Address("::"))


class Stakes(BittensorModel):
    alpha: AlphaStake
    tao: TaoStake
    total: TotalStake


class Neuron(BittensorModel):
    uid: NeuronUid
    coldkey: Coldkey
    hotkey: Hotkey
    active: NeuronActive
    axon_info: AxonInfo
    stake: Stake
    rank: Rank
    emission: Emission
    incentive: Incentive
    consensus: Consensus
    trust: Trust
    validator_trust: ValidatorTrust
    dividends: Dividends
    last_update: Timestamp
    validator_permit: ValidatorPermit
    pruning_score: PruningScore
    # Field below may not be fetched by get_neurons method - it is taken from the subnet's state.
    stakes: Stakes


class SubnetNeurons(BittensorModel):
    block: Block
    neurons: dict[Hotkey, Neuron]


class SubnetValidators(BittensorModel):
    block: Block
    validators: list[Neuron]


class SubnetPriceEntry(BittensorModel):
    value: AlphaPriceRao


class SubnetPrices(BittensorModel):
    block: Block
    prices: dict[NetUid, SubnetPriceEntry]


class SubnetPrice(BittensorModel):
    block: Block
    netuid: NetUid
    price: SubnetPriceEntry


class SubnetHyperparams(BittensorModel):
    tempo: Tempo | None = None
    max_weights_limit: MaxWeightsLimit | None = None
    commit_reveal_weights_enabled: CommitReveal | None = None


class CertificateAlgorithm(UnknownIntEnum):
    ED25519 = 1


class NeuronCertificate(BittensorModel):
    algorithm: CertificateAlgorithm
    public_key: PublicKey


class NeuronCertificateKeypair(NeuronCertificate):
    private_key: PrivateKey


class SubnetState(BittensorModel):
    netuid: NetUid
    hotkeys: list[Hotkey]
    coldkeys: list[Coldkey]
    active: list[SubnetActive]
    validator_permit: list[ValidatorPermit]
    pruning_score: list[PruningScore]
    last_update: list[Timestamp]
    emission: list[EmissionRao]
    dividends: list[Dividends]
    incentives: list[Incentive]
    consensus: list[Consensus]
    trust: list[Trust]
    rank: list[Rank]
    block_at_registration: list[BlockNumber]
    alpha_stake: list[AlphaStakeRao]
    tao_stake: list[TaoStakeRao]
    total_stake: list[TotalStakeRao]
    emission_history: list[list[EmissionRao]]

    @property
    def hotkeys_stakes(self) -> dict[Hotkey, Stakes]:
        return {
            hotkey: Stakes(
                alpha=AlphaStake(Currency[Token.ALPHA].from_rao(alpha)),
                tao=TaoStake(Currency[Token.TAO].from_rao(tao)),
                total=TotalStake(Currency[Token.ALPHA].from_rao(total)),
            )
            for hotkey, alpha, tao, total in zip(self.hotkeys, self.alpha_stake, self.tao_stake, self.total_stake)
        }


class CommitmentKind(StrEnum):
    HEX_DATA = "hex_data"
    TIMELOCK_ENCRYPTED = "timelock_encrypted"


CommitmentKindT = TypeVar("CommitmentKindT", bound=CommitmentKind)


class Commitment(BittensorModel, Generic[CommitmentKindT]):
    kind: CommitmentKindT
    commitment_block_number: BlockNumber
    hotkey: Hotkey
    commitment: CommitmentDataHex


class HexDataCommitment(Commitment[Literal[CommitmentKind.HEX_DATA]]):
    kind: Literal[CommitmentKind.HEX_DATA] = CommitmentKind.HEX_DATA


class TimelockEncryptedCommitment(Commitment[Literal[CommitmentKind.TIMELOCK_ENCRYPTED]]):
    kind: Literal[CommitmentKind.TIMELOCK_ENCRYPTED] = CommitmentKind.TIMELOCK_ENCRYPTED
    reveal_round: int


CommitmentVariant: TypeAlias = Annotated[
    HexDataCommitment | TimelockEncryptedCommitment,
    Field(discriminator="kind"),
]


class SubnetCommitments(BittensorModel):
    block: Block
    commitments: dict[Hotkey, CommitmentVariant]


class RevealedCommitment(BittensorModel):
    reveal_block_number: BlockNumber
    hotkey: Hotkey
    commitment: RevealedCommitmentData


class SubnetRevealedCommitments(BittensorModel):
    block: Block
    commitments: dict[Hotkey, list[RevealedCommitment]]


class ExtrinsicCallArg(BittensorModel):
    """
    Represents a single argument in an extrinsic call.
    """

    model_config = ConfigDict(extra="allow")

    name: str
    type: str
    value: Any


class ExtrinsicCall(BittensorModel):
    """
    Represents the call data within an extrinsic.
    """

    model_config = ConfigDict(extra="allow")

    call_module: str
    call_function: str
    call_args: list[ExtrinsicCallArg]


class Extrinsic(BittensorModel):
    """
    Represents a decoded blockchain extrinsic.

    This model captures the full decoded extrinsic data from the chain.
    Common fields are typed, and any additional fields from the decoded
    extrinsic are preserved via extra="allow".
    """

    model_config = ConfigDict(extra="allow")

    # Block context
    block_number: BlockNumber
    extrinsic_index: ExtrinsicIndex

    # Common extrinsic fields
    extrinsic_hash: ExtrinsicHash
    extrinsic_length: ExtrinsicLength

    # Signer address (None for unsigned extrinsics like timestamp.set)
    address: str | None = None

    # Call information
    call: ExtrinsicCall


class WeightsStatus(BittensorModel):
    weights_submitted: bool


class EvmAssociation(BittensorModel):
    hotkey: Hotkey
    evm_address: EvmAddress
    last_block_where_ownership_was_proven: BlockNumber


class SubnetEvmAssociations(BittensorModel):
    block: Block
    evm_associations: dict[Hotkey, EvmAssociation]
