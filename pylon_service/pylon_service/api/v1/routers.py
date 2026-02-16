from litestar import Router
from pylon_commons.apiver import ApiVersion

from pylon_service.api.v1.api import (
    IdentityController,
    OpenAccessController,
    get_extrinsic_endpoint,
    get_latest_block_info_endpoint,
    identity_login,
)

v1_router = Router(
    path=ApiVersion.V1.prefix,
    route_handlers=[
        IdentityController,
        OpenAccessController,
        identity_login,
        get_extrinsic_endpoint,
        get_latest_block_info_endpoint,
    ],
)
