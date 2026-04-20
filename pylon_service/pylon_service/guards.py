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
from pylon_service.settings import settings

logger = logging.getLogger(__name__)


def extract_bearer_token(connection: ASGIConnection) -> str:
    """
    Extract a Bearer token from the Authorization header.

    Raises:
        NotAuthorizedException: If no Authorization header is provided or format is invalid.
    """
    auth_header = connection.headers.get("Authorization")
    if not auth_header:
        raise NotAuthorizedException(detail="Authorization header is required")

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise NotAuthorizedException(detail="Invalid Authorization header format. Expected: Bearer <token>")

    return parts[1]


def open_access_auth_guard(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    """
    Guard for open access endpoints - validates Bearer token against settings.open_access_token.

    Raises:
        NotAuthorizedException: If no Authorization header is provided or format is invalid (401).
        PermissionDeniedException: If the token doesn't match the configured open access token (403).
    """
    token = extract_bearer_token(connection)
    if not secrets.compare_digest(token, settings.open_access_token):
        raise PermissionDeniedException(detail="Invalid authorization token")


def identity_auth_guard(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    """
    Guard for identity endpoints - validates Bearer token against the identity's configured token.

    Raises:
        NotAuthorizedException: If no Authorization header is provided or format is invalid (401).
        PermissionDeniedException: If the token doesn't match the identity's configured token (403).
        NotFoundException: If the identity does not exist (404).
        InternalServerException: If the guard is applied to a non-identity endpoint (500).
    """
    identity_name = connection.path_params.get("identity_name")
    if identity_name is None:
        raise InternalServerException(detail="Identity guard applied to non-identity endpoint")

    token = extract_bearer_token(connection)
    identity = identities.get(identity_name)
    if identity is None:
        raise NotFoundException(detail=f"Identity '{identity_name}' not found")

    if not secrets.compare_digest(token, identity.token):
        raise PermissionDeniedException(detail="Invalid authorization token")
