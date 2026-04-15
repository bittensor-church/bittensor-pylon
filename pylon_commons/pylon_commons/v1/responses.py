from .._unstable.responses import (  # noqa: F401
    GetAllRevealedCommitmentsResponse,
    GetExtrinsicResponse,
    GetLatestBlockInfoResponse,
    GetNeuronsResponse,
    GetRevealedCommitmentsResponse,
    GetValidatorsResponse,
    IdentityLoginResponse,
    LoginResponse,
    OpenAccessLoginResponse,
    PylonResponse,
    SetCommitmentResponse,
    SetRevealedCommitmentResponse,
    SetWeightsResponse,
)
from ..types import CommitmentDataHex, Hotkey
from .models import Block, Commitment

__all__ = [
    "GetAllRevealedCommitmentsResponse",
    "GetCommitmentResponse",
    "GetCommitmentsResponse",
    "GetExtrinsicResponse",
    "GetLatestBlockInfoResponse",
    "GetNeuronsResponse",
    "GetRevealedCommitmentsResponse",
    "GetValidatorsResponse",
    "IdentityLoginResponse",
    "LoginResponse",
    "OpenAccessLoginResponse",
    "PylonResponse",
    "SetCommitmentResponse",
    "SetRevealedCommitmentResponse",
    "SetWeightsResponse",
]


class GetCommitmentsResponse(PylonResponse):
    """
    V1 response class for the GetCommitmentsRequest.
    """

    block: Block
    commitments: dict[Hotkey, CommitmentDataHex]


class GetCommitmentResponse(PylonResponse, Commitment):
    """
    V1 response class that is returned for the GetCommitmentRequest.
    """

    block: Block
