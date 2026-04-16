import logging
import secrets

from litestar.connection import ASGIConnection
from litestar.exceptions import (
    InternalServerException,
    NotAuthorizedException,
    NotFoundException,
    PermissionDeniedException,
)
from litestar.handlers import BaseRouteHandler

from pylon_service.identities import identities

logger = logging.getLogger(__name__)


def identity_auth_guard(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    """
    Guard for identity endpoints - validates Bearer token against the identity's configured token.

    Raises:
        InternalServerException: If the guard is applied to a non-identity endpoint (500).
        NotAuthorizedException: If no Authorization header is provided or format is invalid (401).
        NotFoundException: If the identity does not exist (404).
        PermissionDeniedException: If the token doesn't match the identity's configured token (403).
    """
    identity_name = connection.path_params.get("identity_name")
    if identity_name is None:
        raise InternalServerException(detail="Identity guard applied to non-identity endpoint")

    auth_header = connection.headers.get("Authorization")
    if not auth_header:
        raise NotAuthorizedException(detail="Authorization header is required")

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise NotAuthorizedException(detail="Invalid Authorization header format. Expected: Bearer <token>")

    token = parts[1]

    identity = identities.get(identity_name)
    if identity is None:
        raise NotFoundException(detail=f"Identity '{identity_name}' not found")

    if not secrets.compare_digest(token, identity.token):
        raise PermissionDeniedException(detail="Invalid authorization token")
