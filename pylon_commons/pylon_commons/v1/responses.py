from .._unstable.responses import (  # noqa: F401
    GetExtrinsicResponse,
    GetLatestBlockInfoResponse,
    GetNeuronsResponse,
    GetValidatorsResponse,
    IdentityLoginResponse,
    LoginResponse,
    OpenAccessLoginResponse,
    PylonResponse,
    SetCommitmentResponse,
    SetWeightsResponse,
)
from ..types import CommitmentDataHex, Hotkey
from .models import Block, Commitment

__all__ = [
    "GetCommitmentResponse",
    "GetCommitmentsResponse",
    "GetExtrinsicResponse",
    "GetLatestBlockInfoResponse",
    "GetNeuronsResponse",
    "GetValidatorsResponse",
    "IdentityLoginResponse",
    "LoginResponse",
    "OpenAccessLoginResponse",
    "PylonResponse",
    "SetCommitmentResponse",
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
