import re
from enum import Enum, unique
from typing import NamedTuple

from pylon._internal.common.apiver import ApiVersion
from pylon._internal.common.types import IdentityName, NetUid


class EndpointMember(NamedTuple):
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

    CERTIFICATES = ("/certificates", "certificates")
    CERTIFICATES_SELF = ("/certificates/self", "certificates_self")
    CERTIFICATES_GENERATE = ("/certificates/self", "certificates_generate")
    CERTIFICATES_HOTKEY = ("/certificates/{hotkey:str}", "certificates_hotkey")
    NEURONS = ("/neurons/{block_number:int}", "neurons")
    LATEST_NEURONS = ("/neurons/latest", "latest_neurons")
    SUBNET_WEIGHTS = ("/weights", "subnet_weights")
    IDENTITY_LOGIN = ("/login/identity/{identity_name:str}", "identity_login")

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
