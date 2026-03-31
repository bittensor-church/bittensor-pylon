from .._unstable.requests import (  # noqa: F401
    AuthenticatedPylonRequest,
    GenerateCertificateKeypairRequest,
    GetExtrinsicRequest,
    GetLatestBlockInfoRequest,
    GetLatestNeuronsRequest,
    GetLatestValidatorsRequest,
    GetNeuronsRequest,
    GetRecentNeuronsRequest,
    GetValidatorsRequest,
    IdentityLoginRequest,
    IdentityPylonRequest,
    LoginResponseT,
    OpenAccessLoginRequest,
    PylonRequest,
    PylonResponseT,
    SetCommitmentRequest,
    SetWeightsRequest,
)
from .responses import GetCommitmentResponse, GetCommitmentsResponse

__all__ = [
    "AuthenticatedPylonRequest",
    "GenerateCertificateKeypairRequest",
    "GetCommitmentRequest",
    "GetCommitmentsRequest",
    "GetExtrinsicRequest",
    "GetLatestBlockInfoRequest",
    "GetLatestNeuronsRequest",
    "GetLatestValidatorsRequest",
    "GetNeuronsRequest",
    "GetOwnCommitmentRequest",
    "GetRecentNeuronsRequest",
    "GetValidatorsRequest",
    "IdentityLoginRequest",
    "IdentityPylonRequest",
    "LoginResponseT",
    "OpenAccessLoginRequest",
    "PylonRequest",
    "PylonResponseT",
    "SetCommitmentRequest",
    "SetWeightsRequest",
]

from ..types import Hotkey


class GetCommitmentsRequest(AuthenticatedPylonRequest[GetCommitmentsResponse]):
    """
    V1 class used to fetch all commitments for the subnet by the Pylon client.
    """

    response_cls = GetCommitmentsResponse


class GetCommitmentRequest(AuthenticatedPylonRequest[GetCommitmentResponse]):
    """
    V1 class used to fetch a commitment for a specific hotkey by the Pylon client.
    """

    response_cls = GetCommitmentResponse

    hotkey: Hotkey


class GetOwnCommitmentRequest(IdentityPylonRequest[GetCommitmentResponse]):
    """
    V1 class used to fetch the commitment for the identity's wallet by the Pylon client.
    """

    response_cls = GetCommitmentResponse
