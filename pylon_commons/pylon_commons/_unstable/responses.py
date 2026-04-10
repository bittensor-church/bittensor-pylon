from pydantic import BaseModel

from ..models import CommitmentVariant
from ..types import IdentityName, NetUid
from .models import (
    Block,
    BlockInfoBag,
    Extrinsic,
    RevealedCommitment,
    SubnetCommitments,
    SubnetNeurons,
    SubnetRevealedCommitments,
    SubnetValidators,
)


class PylonResponse(BaseModel):
    """
    Base class for Pylon response objects.

    Subclasses of this class are returned by the Pylon client, and they contain the relevant information
    returned by the Pylon API.
    Every Pylon request class has its respective response class that will be returned by
    the pylon client after performing a request.
    """


class LoginResponse(PylonResponse):
    """
    Deprecated. Kept for backward compatibility with pylon_client.v1 re-exports; will be removed in 2.0.0.
    """


class OpenAccessLoginResponse(LoginResponse):
    """
    Deprecated. Kept for backward compatibility with pylon_client.v1 re-exports; will be removed in 2.0.0.
    """


class IdentityLoginResponse(LoginResponse):
    """
    Deprecated. Kept for backward compatibility with pylon_client.v1 re-exports; will be removed in 2.0.0.
    """

    netuid: NetUid
    identity_name: IdentityName


class GetIdentitiesResponse(PylonResponse):
    """
    Response returned for the GET /identities request.
    """

    identities: dict[IdentityName, NetUid]


class SetWeightsResponse(PylonResponse):
    """
    Response class that is returned for the SetWeightsRequest.
    """

    # TODO: Modify this model after set weights endpoint is made clean.

    pass


class GetNeuronsResponse(PylonResponse, SubnetNeurons):
    """
    Response class that is returned for the GetNeuronsRequest.
    """

    pass


class GetValidatorsResponse(PylonResponse, SubnetValidators):
    """
    Response class that is returned for the GetValidatorsRequest.
    """

    pass


class SetCommitmentResponse(PylonResponse):
    """
    Response class that is returned for the SetCommitmentRequest.
    """

    pass


class SetRevealedCommitmentResponse(PylonResponse):
    """
    Response class that is returned for the SetRevealedCommitmentRequest.
    """

    reveal_round: int


class GetCommitmentResponse(PylonResponse):
    """
    Response class that is returned for the GetCommitmentRequest.
    """

    commitment: CommitmentVariant
    block: Block


class GetRevealedCommitmentsResponse(PylonResponse):
    """
    Response class that is returned for the GetRevealedCommitmentsRequest.
    """

    commitments: list[RevealedCommitment]
    block: Block


class GetCommitmentsResponse(PylonResponse, SubnetCommitments):
    """
    Response class that is returned for the GetCommitmentsRequest.
    """

    pass


class GetAllRevealedCommitmentsResponse(PylonResponse, SubnetRevealedCommitments):
    """
    Response class that is returned for the GetAllRevealedCommitmentsRequest.
    """

    pass


class GetLatestBlockInfoResponse(PylonResponse, BlockInfoBag):
    """
    Response class that is returned for the GetLatestBlockInfoRequest.
    """

    pass


class GetExtrinsicResponse(PylonResponse, Extrinsic):
    """
    Response class that is returned for the GetExtrinsicRequest.
    """

    pass


class GetDrandLastStoredRoundResponse(PylonResponse):
    """
    Response class that is returned for the GetDrandLastStoredRoundRequest.
    """

    last_stored_round: int
