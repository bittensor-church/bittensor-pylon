from enum import nonmember, unique
from http import HTTPMethod

from ..apiver import ApiVersion
from ..endpoints import Endpoint as BaseEndpoint

__all__ = ["Endpoint"]


@unique
class Endpoint(BaseEndpoint):
    """
    V1 API endpoint path definitions.

    Mirrors the unstable Endpoint with _v1 suffix on reverse names.
    """

    _version = nonmember(ApiVersion.V1)  # type: ignore[reportAssignmentType]

    CERTIFICATES = (HTTPMethod.GET, "/block/latest/certificates", "certificates_v1")
    CERTIFICATES_GENERATE = (HTTPMethod.POST, "/certificates/self", "certificates_generate_v1")
    CERTIFICATES_HOTKEY = (HTTPMethod.GET, "/block/latest/certificates/{hotkey:str}", "certificates_hotkey_v1")
    CERTIFICATES_SELF = (HTTPMethod.GET, "/block/latest/certificates/self", "certificates_self_v1")
    COMMITMENTS = (HTTPMethod.POST, "/commitments", "commitments_v1")
    EXTRINSIC = (HTTPMethod.GET, "/block/{block_number:int}/extrinsic/{extrinsic_index:int}", "extrinsic_v1")
    IDENTITY_LOGIN = (HTTPMethod.POST, "/login/identity/{identity_name:str}", "identity_login_v1")
    LATEST_BLOCK_INFO = (HTTPMethod.GET, "/block/latest", "latest_block_info")
    LATEST_COMMITMENTS = (HTTPMethod.GET, "/block/latest/commitments", "latest_commitments_v1")
    LATEST_COMMITMENTS_HOTKEY = (
        HTTPMethod.GET,
        "/block/latest/commitments/{hotkey:str}",
        "latest_commitments_hotkey_v1",
    )
    LATEST_COMMITMENTS_SELF = (HTTPMethod.GET, "/block/latest/commitments/self", "latest_commitments_self_v1")
    LATEST_NEURONS = (HTTPMethod.GET, "/block/latest/neurons", "latest_neurons_v1")
    LATEST_VALIDATORS = (HTTPMethod.GET, "/block/latest/validators", "latest_validators_v1")
    NEURONS = (HTTPMethod.GET, "/block/{block_number:int}/neurons", "neurons_v1")
    RECENT_NEURONS = (HTTPMethod.GET, "/block/recent/neurons", "recent_neurons_v1")
    SUBNET_WEIGHTS = (HTTPMethod.PUT, "/weights", "subnet_weights_v1")
    VALIDATORS = (HTTPMethod.GET, "/block/{block_number:int}/validators", "validators_v1")
