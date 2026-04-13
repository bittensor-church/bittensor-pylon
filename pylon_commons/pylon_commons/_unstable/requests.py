import re
import typing

from pydantic import BaseModel, Field, field_validator

from ..apiver import ApiVersion
from ..types import BlockNumber, ExtrinsicIndex, Hotkey, IdentityName, NetUid
from .bodies import LoginBody, SetCommitmentBody, SetRevealedCommitmentBody, SetWeightsBody
from .models import CertificateAlgorithm
from .responses import (
    GetAllRevealedCommitmentsResponse,
    GetCommitmentResponse,
    GetCommitmentsResponse,
    GetDrandLastStoredRoundResponse,
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

PylonResponseT = typing.TypeVar("PylonResponseT", bound=PylonResponse, covariant=True)
LoginResponseT = typing.TypeVar("LoginResponseT", bound=LoginResponse, covariant=True)


class PylonRequest(BaseModel, typing.Generic[PylonResponseT]):
    """
    Base class for all Pylon requests.

    Pylon requests are objects supplied to the Pylon client to make a request. Each class represents an action
    (e.g., setting weights) and defines arguments needed to perform the action.
    Every Pylon request class has its respective response class that will be returned by
    the pylon client after performing a request.
    """

    response_cls: typing.ClassVar[type[PylonResponseT]]  # type: ignore[reportGeneralTypeIssues]

    api_version: ApiVersion = Field(default=ApiVersion.UNSTABLE, exclude=True)

    @property
    def request_type(self) -> str:
        name = type(self).__name__.removesuffix("Request")
        return re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", name).lower()


# Request classes used to log in into Pylon


class OpenAccessLoginRequest(LoginBody, PylonRequest[OpenAccessLoginResponse]):
    response_cls = OpenAccessLoginResponse


class IdentityLoginRequest(LoginBody, PylonRequest[IdentityLoginResponse]):
    response_cls = IdentityLoginResponse

    identity_name: IdentityName


# Request classes for endpoints that require authentication either by open access or identity


class AuthenticatedPylonRequest(PylonRequest[PylonResponseT], typing.Generic[PylonResponseT]):
    """
    Request that requires the authentication, either by open access or identity.
    """

    netuid: NetUid
    # None == open access
    identity_name: IdentityName | None = None


class GetNeuronsRequest(AuthenticatedPylonRequest[GetNeuronsResponse]):
    """
    Class used to fetch the neurons by the Pylon client.
    """

    response_cls = GetNeuronsResponse

    block_number: BlockNumber


class GetLatestNeuronsRequest(AuthenticatedPylonRequest[GetNeuronsResponse]):
    """
    Class used to fetch the latest neurons by the Pylon client.
    """

    response_cls = GetNeuronsResponse


class GetRecentNeuronsRequest(AuthenticatedPylonRequest[GetNeuronsResponse]):
    """
    Class used to fetch the cached neurons by the Pylon client.
    """

    response_cls = GetNeuronsResponse


class GetValidatorsRequest(AuthenticatedPylonRequest[GetValidatorsResponse]):
    """
    Class used to fetch the validators by the Pylon client.
    """

    response_cls = GetValidatorsResponse

    block_number: BlockNumber


class GetLatestValidatorsRequest(AuthenticatedPylonRequest[GetValidatorsResponse]):
    """
    Class used to fetch the latest validators by the Pylon client.
    """

    response_cls = GetValidatorsResponse


class GetCommitmentRequest(AuthenticatedPylonRequest[GetCommitmentResponse]):
    """
    Class used to fetch a commitment for a specific hotkey by the Pylon client.
    """

    response_cls = GetCommitmentResponse

    hotkey: Hotkey


class GetRevealedCommitmentsRequest(AuthenticatedPylonRequest[GetRevealedCommitmentsResponse]):
    """
    Class used to fetch revealed commitments for a specific hotkey by the Pylon client.
    """

    response_cls = GetRevealedCommitmentsResponse
    hotkey: Hotkey


class GetCommitmentsRequest(AuthenticatedPylonRequest[GetCommitmentsResponse]):
    """
    Class used to fetch all commitments for the subnet by the Pylon client.
    """

    response_cls = GetCommitmentsResponse


class GetAllRevealedCommitmentsRequest(AuthenticatedPylonRequest[GetAllRevealedCommitmentsResponse]):
    """
    Class used to fetch all revealed commitments for the subnet by the Pylon client.
    """

    response_cls = GetAllRevealedCommitmentsResponse


class GetLatestBlockInfoRequest(PylonRequest[GetLatestBlockInfoResponse]):
    """
    Class used to fetch latest block info by the Pylon client.

    This request does not require subnet context as blocks are blockchain-level data.
    """

    response_cls = GetLatestBlockInfoResponse


class GetExtrinsicRequest(PylonRequest[GetExtrinsicResponse]):
    """
    Class used to fetch an extrinsic from a specific block by the Pylon client.

    This request does not require subnet context as extrinsics are block-level data.
    """

    response_cls = GetExtrinsicResponse

    block_number: BlockNumber
    extrinsic_index: ExtrinsicIndex


class GetDrandLastStoredRoundRequest(PylonRequest[GetDrandLastStoredRoundResponse]):
    """
    Class used to fetch the last stored round for drand by the Pylon client.

    This request does not require subnet context as it is block-level data.
    """

    response_cls = GetDrandLastStoredRoundResponse


# Request classes that require identity authentication.


class IdentityPylonRequest(AuthenticatedPylonRequest[PylonResponseT], typing.Generic[PylonResponseT]):
    """
    Request that requires authentication via identity.
    """

    identity_name: IdentityName  # type: ignore[assignment]


class SetWeightsRequest(SetWeightsBody, IdentityPylonRequest[SetWeightsResponse]):
    """
    Class used to perform setting weights by the Pylon client.
    """

    response_cls = SetWeightsResponse


class SetCommitmentRequest(SetCommitmentBody, IdentityPylonRequest[SetCommitmentResponse]):
    """
    Class used to set a commitment (model metadata) on chain by the Pylon client.
    """

    response_cls = SetCommitmentResponse


class SetRevealedCommitmentRequest(SetRevealedCommitmentBody, IdentityPylonRequest[SetRevealedCommitmentResponse]):
    """
    Class used to set a revealed commitment (model metadata) on chain by the Pylon client.
    """

    response_cls = SetRevealedCommitmentResponse


class GetOwnCommitmentRequest(IdentityPylonRequest[GetCommitmentResponse]):
    """
    Class used to fetch the commitment for the identity's wallet by the Pylon client.
    """

    response_cls = GetCommitmentResponse


class GetOwnRevealedCommitmentsRequest(IdentityPylonRequest[GetRevealedCommitmentsResponse]):
    """
    Class used to fetch revealed commitments for the identity's wallet by the Pylon client.
    """

    response_cls = GetRevealedCommitmentsResponse


class GenerateCertificateKeypairRequest(PylonRequest):
    algorithm: CertificateAlgorithm = CertificateAlgorithm.ED25519

    @field_validator("algorithm", mode="before")
    @classmethod
    def validate_algorithm(cls, v):
        if v != CertificateAlgorithm.ED25519:
            raise ValueError("Currently, only algorithm equals 1 is supported which is EdDSA using Ed25519 curve")
        return v
