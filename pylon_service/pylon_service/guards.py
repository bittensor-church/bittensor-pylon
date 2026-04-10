import logging
import secrets

from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException, PermissionDeniedException
from litestar.handlers import BaseRouteHandler

from pylon_service.identities import identities

logger = logging.getLogger(__name__)


def identity_auth_guard(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    """
    Guard for identity endpoints - validates Bearer token against the identity's configured token.

    Raises:
        NotAuthorizedException: If no Authorization header is provided or format is invalid (401).
        PermissionDeniedException: If the token doesn't match the identity's configured token (403).
    """
    auth_header = connection.headers.get("Authorization")
    if not auth_header:
        raise NotAuthorizedException(detail="Authorization header is required")

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise NotAuthorizedException(detail="Invalid Authorization header format. Expected: Bearer <token>")

    token = parts[1]
    identity_name = connection.path_params.get("identity_name")
    if identity_name is None:
        return

    identity = identities.get(identity_name)
    if identity is None:
        # Let identity_dep handle 404 for unknown identities
        return

    if not secrets.compare_digest(token, identity.token):
        raise PermissionDeniedException(detail="Invalid authorization token")
