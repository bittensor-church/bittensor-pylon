from litestar import Router
from pylon_commons.apiver import ApiVersion

from pylon_service.api._unstable.api import (
    IdentityController,
    OpenAccessController,
    get_extrinsic_endpoint,
    identity_login,
)

unstable_router = Router(
    path=ApiVersion.UNSTABLE.prefix,
    route_handlers=[IdentityController, OpenAccessController, identity_login, get_extrinsic_endpoint],
)
