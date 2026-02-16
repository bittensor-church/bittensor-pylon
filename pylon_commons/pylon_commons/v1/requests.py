from .._unstable.requests import (  # noqa: F401
    AuthenticatedPylonRequest,
    GenerateCertificateKeypairRequest,
    GetCommitmentRequest,
    GetExtrinsicRequest,
    GetLatestBlockInfoRequest,
    GetLatestNeuronsRequest,
    GetLatestValidatorsRequest,
    GetNeuronsRequest,
    GetOwnCommitmentRequest,
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
from .responses import GetCommitmentsResponse

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


class GetCommitmentsRequest(AuthenticatedPylonRequest[GetCommitmentsResponse]):
    """
    V1 class used to fetch all commitments for the subnet by the Pylon client.
    """

    response_cls = GetCommitmentsResponse
