import re
from enum import Enum, nonmember, unique
from http import HTTPMethod
from typing import NamedTuple

from .apiver import ApiVersion
from .types import IdentityName, NetUid


class EndpointMember(NamedTuple):
    method: HTTPMethod
    url: str
    reverse: str


class Endpoint(EndpointMember, Enum):
    """
    Base class for versioned endpoint enums.

    Subclasses must define a `version` class variable and their endpoint members.
    """

    _version: ApiVersion

    def format_url(self, *args, **kwargs) -> str:
        normalized = re.sub(r":.+?}", "}", self.url)
        return normalized.format(*args, **kwargs)

    def absolute_url(self, netuid_: NetUid | None = None, identity_name_: IdentityName | None = None, **kwargs):
        formatted_endpoint = self.format_url(**kwargs)
        netuid_part = f"/subnet/{netuid_}" if netuid_ is not None else ""
        identity_part = f"/identity/{identity_name_}" if identity_name_ is not None else ""
        return f"{self._version.prefix}{identity_part}{netuid_part}{formatted_endpoint}"

    @classmethod
    def version(cls, version: ApiVersion):
        return {
            ApiVersion.V1: EndpointV1,
            ApiVersion.V2: EndpointV2,
        }[version]


@unique
class EndpointV1(Endpoint):
    """
    V1 API endpoint path definitions.

    IMPORTANT: Each route handler must have its own unique enum member.
    Even if multiple handlers share the same path (e.g., different HTTP methods),
    they must have separate enum members to ensure unique reverse names in Litestar.
    """

    _version = nonmember(ApiVersion.V1)  # type: ignore[reportAssignmentType]

    CERTIFICATES = (HTTPMethod.GET, "/block/latest/certificates", "certificates")
    CERTIFICATES_SELF = (HTTPMethod.GET, "/block/latest/certificates/self", "certificates_self")
    CERTIFICATES_GENERATE = (HTTPMethod.POST, "/certificates/self", "certificates_generate")
    CERTIFICATES_HOTKEY = (HTTPMethod.GET, "/block/latest/certificates/{hotkey:str}", "certificates_hotkey")
    NEURONS = (HTTPMethod.GET, "/block/{block_number:int}/neurons", "neurons")
    LATEST_NEURONS = (HTTPMethod.GET, "/block/latest/neurons", "latest_neurons")
    RECENT_NEURONS = (HTTPMethod.GET, "/block/recent/neurons", "recent_neurons")
    LATEST_BLOCK_INFO = (HTTPMethod.GET, "/block/latest", "latest_block_info")
    VALIDATORS = (HTTPMethod.GET, "/block/{block_number:int}/validators", "validators")
    LATEST_VALIDATORS = (HTTPMethod.GET, "/block/latest/validators", "latest_validators")
    SUBNET_WEIGHTS = (HTTPMethod.PUT, "/weights", "subnet_weights")
    IDENTITY_LOGIN = (HTTPMethod.POST, "/login/identity/{identity_name:str}", "identity_login")
    COMMITMENTS = (HTTPMethod.POST, "/commitments", "commitments")
    LATEST_COMMITMENTS = (HTTPMethod.GET, "/block/latest/commitments", "latest_commitments")
    LATEST_COMMITMENTS_HOTKEY = (HTTPMethod.GET, "/block/latest/commitments/{hotkey:str}", "latest_commitments_hotkey")
    LATEST_COMMITMENTS_SELF = (HTTPMethod.GET, "/block/latest/commitments/self", "latest_commitments_self")
    EXTRINSIC = (HTTPMethod.GET, "/block/{block_number:int}/extrinsic/{extrinsic_index:int}", "extrinsic")


@unique
class EndpointV2(Endpoint):
    """
    V2 API endpoint path definitions.

    Contains only endpoints that have breaking changes from V1.
    """

    _version = nonmember(ApiVersion.V2)  # type: ignore[reportAssignmentType]

    LATEST_COMMITMENTS = (HTTPMethod.GET, "/block/latest/commitments", "latest_commitments_v2")
