from litestar import Router
from pylon_commons.apiver import ApiVersion

from pylon_service._unstable.api import IdentityController, OpenAccessController

unstable_router = Router(
    path=ApiVersion.UNSTABLE.prefix,
    route_handlers=[IdentityController, OpenAccessController],
)
