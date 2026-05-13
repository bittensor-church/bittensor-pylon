from litestar import Router
from pylon_commons.apiver import ApiVersion

from pylon_service.api.v1.api import (
    IdentityController,
    OpenAccessController,
    PublicController,
)

v1_router = Router(
    path=ApiVersion.V1.prefix,
    route_handlers=[
        IdentityController,
        OpenAccessController,
        PublicController,
    ],
)
