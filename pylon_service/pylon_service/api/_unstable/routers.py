from litestar import Router
from pylon_commons.apiver import ApiVersion

from pylon_service.api._unstable.api import (
    IdentityController,
    OpenAccessController,
    get_extrinsic_endpoint,
    get_latest_block_info_endpoint,
    identity_login,
)
from pylon_service.api.exception_handlers import domain_exception_handlers

unstable_router = Router(
    path=ApiVersion.UNSTABLE.prefix,
    route_handlers=[
        IdentityController,
        OpenAccessController,
        identity_login,
        get_extrinsic_endpoint,
        get_latest_block_info_endpoint,
    ],
    exception_handlers=dict(domain_exception_handlers),
)
