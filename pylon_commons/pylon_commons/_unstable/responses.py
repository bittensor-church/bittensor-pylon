from ..responses import PylonResponse
from .models import SubnetCommitments


class GetCommitmentsResponseUnstable(PylonResponse, SubnetCommitments):
    """
    Response class that is returned for the GetCommitmentsRequestUnstable.

    Includes commitment data with commitment_block_number for each hotkey.
    """

    pass
