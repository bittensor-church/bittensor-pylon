import re
from enum import Enum, unique
from http import HTTPMethod
from typing import NamedTuple

from pylon_client._internal.common.apiver import ApiVersion
from pylon_client._internal.common.types import IdentityName, NetUid


class EndpointMember(NamedTuple):
    method: HTTPMethod
    url: str
    reverse: str


@unique
class Endpoint(EndpointMember, Enum):
    """
    Endpoint path definitions for the API.

    IMPORTANT: Each route handler must have its own unique enum member.
    Even if multiple handlers share the same path (e.g., different HTTP methods),
    they must have separate enum members to ensure unique reverse names in Litestar.
    """

    CERTIFICATES = (HTTPMethod.GET, "/block/latest/certificates", "certificates")
    CERTIFICATES_SELF = (HTTPMethod.GET, "/block/latest/certificates/self", "certificates_self")
    CERTIFICATES_GENERATE = (HTTPMethod.POST, "/certificates/self", "certificates_generate")
    CERTIFICATES_HOTKEY = (HTTPMethod.GET, "/block/latest/certificates/{hotkey:str}", "certificates_hotkey")
    NEURONS = (HTTPMethod.GET, "/block/{block_number:int}/neurons", "neurons")
    LATEST_NEURONS = (HTTPMethod.GET, "/block/latest/neurons", "latest_neurons")
    RECENT_NEURONS = (HTTPMethod.GET, "/block/recent/neurons", "recent_neurons")
    VALIDATORS = (HTTPMethod.GET, "/block/{block_number:int}/validators", "validators")
    LATEST_VALIDATORS = (HTTPMethod.GET, "/block/latest/validators", "latest_validators")
    SUBNET_WEIGHTS = (HTTPMethod.PUT, "/weights", "subnet_weights")
    IDENTITY_LOGIN = (HTTPMethod.POST, "/login/identity/{identity_name:str}", "identity_login")
    COMMITMENTS = (HTTPMethod.POST, "/commitments", "commitments")
    LATEST_COMMITMENTS = (HTTPMethod.GET, "/block/latest/commitments", "latest_commitments")
    LATEST_COMMITMENTS_HOTKEY = (HTTPMethod.GET, "/block/latest/commitments/{hotkey:str}", "latest_commitments_hotkey")
    LATEST_COMMITMENTS_SELF = (HTTPMethod.GET, "/block/latest/commitments/self", "latest_commitments_self")

    def format_url(self, *args, **kwargs) -> str:
        normalized = re.sub(r":.+?}", "}", self.url)
        return normalized.format(*args, **kwargs)

    def absolute_url(
        self, version: ApiVersion, netuid_: NetUid | None = None, identity_name_: IdentityName | None = None, **kwargs
    ):
        formatted_endpoint = self.format_url(**kwargs)
        netuid_part = f"/subnet/{netuid_}" if netuid_ is not None else ""
        identity_part = f"/identity/{identity_name_}" if identity_name_ is not None else ""
        return f"{version.prefix}{identity_part}{netuid_part}{formatted_endpoint}"
