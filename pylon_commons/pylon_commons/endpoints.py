import re
from enum import Enum
from typing import NamedTuple

from .apiver import ApiVersion
from .types import IdentityName, NetUid


class EndpointMember(NamedTuple):
    method: str
    url: str
    reverse: str


class Endpoint(EndpointMember, Enum):
    """
    Base class for versioned endpoint enums.

    Subclasses must define a `_version` class variable and their endpoint members.
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
