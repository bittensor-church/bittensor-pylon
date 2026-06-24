"""
Custom Prometheus controller with Bearer token authorization using Litestar Guards.

Uses Litestar's built-in PrometheusController with custom authentication guard
instead of implementing a custom endpoint from scratch.
"""

import secrets

import structlog
from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException, PermissionDeniedException
from litestar.handlers import BaseRouteHandler
from litestar.plugins.prometheus.controller import PrometheusController

from pylon_service.guards import extract_bearer_token
from pylon_service.settings import settings

logger = structlog.stdlib.get_logger(__name__)


def metrics_auth_guard(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    """
    Guard for /metrics endpoint - validates Bearer token.

    Raises:
        NotAuthorizedException: If no Authorization header is provided or format is invalid (401).
        PermissionDeniedException: If metrics are disabled or credentials are missing/invalid (403).
    """
    if not settings.metrics_token:
        logger.warning("metrics_token_not_configured")
        raise PermissionDeniedException(detail="Metrics endpoint is not configured")

    try:
        token = extract_bearer_token(connection)
    except NotAuthorizedException:
        logger.warning("metrics_invalid_auth_header")
        raise

    if not secrets.compare_digest(token, settings.metrics_token):
        logger.warning("metrics_invalid_token")
        raise PermissionDeniedException(detail="Invalid authorization token")


class AuthenticatedPrometheusController(PrometheusController):
    """
    PrometheusController with Bearer token authentication.
    """

    guards = [metrics_auth_guard]
