from litestar import Router

from pylon_client._internal.common.apiver import ApiVersion
from pylon_client.service.api import (
    IdentityController,
    OpenAccessController,
    identity_login,
)

v1_router = Router(
    path=ApiVersion.V1.prefix,
    route_handlers=[IdentityController, OpenAccessController, identity_login],
)
