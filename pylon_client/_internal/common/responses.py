from pydantic import BaseModel

from pylon_client._internal.common.models import Commitment, SubnetCommitments, SubnetNeurons, SubnetValidators
from pylon_client._internal.common.types import IdentityName, NetUid


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
    Base class for response that is returned for the login request.
    """

    pass


class OpenAccessLoginResponse(LoginResponse):
    """
    Response returned for the login via open access request.
    """

    pass


class IdentityLoginResponse(LoginResponse):
    """
    Response returned for the login via identity request.
    """

    netuid: NetUid
    identity_name: IdentityName


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


class GetCommitmentResponse(PylonResponse, Commitment):
    """
    Response class that is returned for the GetCommitmentRequest.
    """

    pass


class GetCommitmentsResponse(PylonResponse, SubnetCommitments):
    """
    Response class that is returned for the GetCommitmentsRequest.
    """

    pass
