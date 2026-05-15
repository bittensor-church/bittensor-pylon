from litestar import Router
from pylon_commons.apiver import ApiVersion

from pylon_service.api._unstable.api import (
    IdentityController,
    OpenAccessController,
    PublicController,
)

unstable_router = Router(
    path=ApiVersion.UNSTABLE.prefix,
    route_handlers=[
        IdentityController,
        OpenAccessController,
        PublicController,
    ],
)
