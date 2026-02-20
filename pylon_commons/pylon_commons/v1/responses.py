from .._unstable.responses import (  # noqa: F401
    GetCommitmentResponse,
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
from .models import Block

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
