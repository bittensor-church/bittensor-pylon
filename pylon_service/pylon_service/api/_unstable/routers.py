from litestar import Router
from pylon_commons.apiver import ApiVersion

from pylon_service.api._unstable.api import (
    IdentityController,
    OpenAccessController,
    get_extrinsic_endpoint,
    get_identities,
    get_last_stored_round_endpoint,
    get_latest_block_info_endpoint,
)

unstable_router = Router(
    path=ApiVersion.UNSTABLE.prefix,
    route_handlers=[
        IdentityController,
        OpenAccessController,
        get_identities,
        get_extrinsic_endpoint,
        get_last_stored_round_endpoint,
        get_latest_block_info_endpoint,
    ],
)
