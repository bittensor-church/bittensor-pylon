from enum import nonmember, unique
from http import HTTPMethod

from ..apiver import ApiVersion
from ..endpoints import Endpoint as BaseEndpoint


@unique
class Endpoint(BaseEndpoint):
    """
    Unstable API endpoint path definitions.

    This is the canonical set of all endpoint members. v1/endpoints.py
    duplicates these with a _v1 suffix on reverse names.

    IMPORTANT: Each route handler must have its own unique enum member.
    Even if multiple handlers share the same path (e.g., different HTTP methods),
    they must have separate enum members to ensure unique reverse names in Litestar.
    """

    _version = nonmember(ApiVersion.UNSTABLE)  # type: ignore[reportAssignmentType]

    CERTIFICATES = (HTTPMethod.GET, "/block/latest/certificates", "certificates")
    CERTIFICATES_GENERATE = (HTTPMethod.POST, "/certificates/self", "certificates_generate")
    CERTIFICATES_HOTKEY = (HTTPMethod.GET, "/block/latest/certificates/{hotkey:str}", "certificates_hotkey")
    CERTIFICATES_SELF = (HTTPMethod.GET, "/block/latest/certificates/self", "certificates_self")
    COMMITMENTS = (HTTPMethod.POST, "/commitments", "commitments")
    EXTRINSIC = (HTTPMethod.GET, "/block/{block_number:int}/extrinsic/{extrinsic_index:int}", "extrinsic")
    IDENTITY_LOGIN = (HTTPMethod.POST, "/login/identity/{identity_name:str}", "identity_login")
    LATEST_BLOCK_INFO = (HTTPMethod.GET, "/block/latest", "latest_block_info")
    LATEST_COMMITMENTS = (HTTPMethod.GET, "/block/latest/commitments", "latest_commitments")
    LATEST_COMMITMENTS_HOTKEY = (HTTPMethod.GET, "/block/latest/commitments/{hotkey:str}", "latest_commitments_hotkey")
    LATEST_COMMITMENTS_SELF = (HTTPMethod.GET, "/block/latest/commitments/self", "latest_commitments_self")
    LATEST_NEURONS = (HTTPMethod.GET, "/block/latest/neurons", "latest_neurons")
    LATEST_VALIDATORS = (HTTPMethod.GET, "/block/latest/validators", "latest_validators")
    NEURONS = (HTTPMethod.GET, "/block/{block_number:int}/neurons", "neurons")
    RECENT_NEURONS = (HTTPMethod.GET, "/block/recent/neurons", "recent_neurons")
    SUBNET_WEIGHTS = (HTTPMethod.PUT, "/weights", "subnet_weights")
    VALIDATORS = (HTTPMethod.GET, "/block/{block_number:int}/validators", "validators")
