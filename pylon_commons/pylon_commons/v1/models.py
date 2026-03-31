from .._unstable.models import (
    AxonInfo,
    AxonProtocol,
    BittensorModel,
    Block,
    BlockInfoBag,
    CertificateAlgorithm,
    CommitReveal,
    Extrinsic,
    ExtrinsicCall,
    ExtrinsicCallArg,
    Neuron,
    NeuronCertificate,
    NeuronCertificateKeypair,
    Stakes,
    SubnetCommitments,
    SubnetHyperparams,
    SubnetNeurons,
    SubnetState,
    SubnetValidators,
    UnknownIntEnum,
)
from ..types import BlockNumber, CommitmentDataHex, Hotkey


class Commitment(BittensorModel):
    commitment_block_number: BlockNumber
    hotkey: Hotkey
    commitment: CommitmentDataHex
