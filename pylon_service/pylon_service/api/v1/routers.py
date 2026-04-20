from litestar import Router
from pylon_commons.apiver import ApiVersion

from pylon_service.api.v1.api import (
    IdentityController,
    OpenAccessController,
    get_extrinsic_endpoint,
    get_identities,
    get_latest_block_info_endpoint,
)

v1_router = Router(
    path=ApiVersion.V1.prefix,
    route_handlers=[
        IdentityController,
        OpenAccessController,
        get_identities,
        get_extrinsic_endpoint,
        get_latest_block_info_endpoint,
    ],
)
