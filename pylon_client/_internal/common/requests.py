import typing

from pydantic import BaseModel, field_validator

from pylon_client._internal.common.apiver import ApiVersion
from pylon_client._internal.common.bodies import LoginBody, SetCommitmentBody, SetWeightsBody
from pylon_client._internal.common.models import CertificateAlgorithm
from pylon_client._internal.common.responses import (
    GetCommitmentResponse,
    GetCommitmentsResponse,
    GetNeuronsResponse,
    GetValidatorsResponse,
    IdentityLoginResponse,
    LoginResponse,
    OpenAccessLoginResponse,
    PylonResponse,
    SetCommitmentResponse,
    SetWeightsResponse,
)
from pylon_client._internal.common.types import BlockNumber, Hotkey, IdentityName, NetUid

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

    version: typing.ClassVar[ApiVersion]
    response_cls: typing.ClassVar[type[PylonResponseT]]  # type: ignore[reportGeneralTypeIssues]


# Request classes used to log in into Pylon


class OpenAccessLoginRequest(LoginBody, PylonRequest[OpenAccessLoginResponse]):
    version = ApiVersion.V1
    response_cls = OpenAccessLoginResponse


class IdentityLoginRequest(LoginBody, PylonRequest[IdentityLoginResponse]):
    version = ApiVersion.V1
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

    version = ApiVersion.V1
    response_cls = GetNeuronsResponse

    block_number: BlockNumber


class GetLatestNeuronsRequest(AuthenticatedPylonRequest[GetNeuronsResponse]):
    """
    Class used to fetch the latest neurons by the Pylon client.
    """

    version = ApiVersion.V1
    response_cls = GetNeuronsResponse


class GetRecentNeuronsRequest(AuthenticatedPylonRequest[GetNeuronsResponse]):
    """
    Class used to fetch the cached neurons by the Pylon client.
    """

    version = ApiVersion.V1
    response_cls = GetNeuronsResponse


class GetValidatorsRequest(AuthenticatedPylonRequest[GetValidatorsResponse]):
    """
    Class used to fetch the validators by the Pylon client.
    """

    version = ApiVersion.V1
    response_cls = GetValidatorsResponse

    block_number: BlockNumber


class GetLatestValidatorsRequest(AuthenticatedPylonRequest[GetValidatorsResponse]):
    """
    Class used to fetch the latest validators by the Pylon client.
    """

    version = ApiVersion.V1
    response_cls = GetValidatorsResponse


class GetCommitmentRequest(AuthenticatedPylonRequest[GetCommitmentResponse]):
    """
    Class used to fetch a commitment for a specific hotkey by the Pylon client.
    """

    version = ApiVersion.V1
    response_cls = GetCommitmentResponse

    hotkey: Hotkey


class GetCommitmentsRequest(AuthenticatedPylonRequest[GetCommitmentsResponse]):
    """
    Class used to fetch all commitments for the subnet by the Pylon client.
    """

    version = ApiVersion.V1
    response_cls = GetCommitmentsResponse


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

    version = ApiVersion.V1
    response_cls = SetWeightsResponse


class SetCommitmentRequest(SetCommitmentBody, IdentityPylonRequest[SetCommitmentResponse]):
    """
    Class used to set a commitment (model metadata) on chain by the Pylon client.
    """

    version = ApiVersion.V1
    response_cls = SetCommitmentResponse


class GetOwnCommitmentRequest(IdentityPylonRequest[GetCommitmentResponse]):
    """
    Class used to fetch the commitment for the identity's wallet by the Pylon client.
    """

    version = ApiVersion.V1
    response_cls = GetCommitmentResponse


class GenerateCertificateKeypairRequest(PylonRequest):
    algorithm: CertificateAlgorithm = CertificateAlgorithm.ED25519

    @field_validator("algorithm", mode="before")
    @classmethod
    def validate_algorithm(cls, v):
        if v != CertificateAlgorithm.ED25519:
            raise ValueError("Currently, only algorithm equals 1 is supported which is EdDSA using Ed25519 curve")
        return v
