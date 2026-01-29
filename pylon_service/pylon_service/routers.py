from litestar import Router
from pylon_commons.apiver import ApiVersion

from pylon_service.api import (
    IdentityController,
    IdentityControllerV2,
    OpenAccessController,
    OpenAccessControllerV2,
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

v2_router = Router(
    path=ApiVersion.V2.prefix,
    route_handlers=[IdentityControllerV2, OpenAccessControllerV2],
)
