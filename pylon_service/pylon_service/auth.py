"""
Session-based authentication for identity endpoints.
"""

from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException, PermissionDeniedException
from litestar.handlers import BaseRouteHandler
from litestar.middleware.session.server_side import ServerSideSessionConfig

from pylon_service.stores import StoreName

session_config = ServerSideSessionConfig(store=StoreName.SESSIONS)


def identity_session_guard(connection: ASGIConnection, _handler: BaseRouteHandler) -> None:
    """
    Guard that verifies the request has an active session for the requested identity and netuid.

    Raises:
        NotAuthorizedException: If no session exists or the identity is not logged in.
        PermissionDeniedException: If the session identity's netuid does not match the requested netuid.
    """
    identity_name = connection.path_params.get("identity_name")
    netuid = connection.path_params.get("netuid")

    session_identities = connection.session.get("identities", {})
    identity_data = session_identities.get(identity_name)

    if not identity_data:
        raise NotAuthorizedException(detail="Not authenticated")

    if identity_data.get("netuid") != netuid:
        raise PermissionDeniedException(detail="Session netuid does not match requested netuid")
