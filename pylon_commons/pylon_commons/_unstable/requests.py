from ..requests import AuthenticatedPylonRequest
from .responses import GetCommitmentsResponseUnstable


class GetCommitmentsRequestUnstable(AuthenticatedPylonRequest[GetCommitmentsResponseUnstable]):
    """
    Class used to fetch all commitments for the subnet by the Pylon client (unstable).

    Returns rich commitment data including commitment_block_number for each hotkey.
    """

    response_cls = GetCommitmentsResponseUnstable
