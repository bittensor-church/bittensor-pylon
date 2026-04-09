from typing import NoReturn

from litestar import Request
from litestar.exceptions import NotFoundException, ServiceUnavailableException

from pylon_service.exceptions import BadGatewayException
from pylon_service.services.errors import (
    BlockNotFoundError,
    CertificateGenerationFailedError,
    CertificateNotFoundError,
    CommitmentNotFoundError,
    ExtrinsicNotFoundError,
    RecentObjectMissingError,
    RecentObjectStaleError,
)


def handle_not_found(_: Request, exc: Exception) -> NoReturn:
    raise NotFoundException(detail=str(exc)) from exc


def handle_service_unavailable(_: Request, exc: Exception) -> NoReturn:
    raise ServiceUnavailableException(detail=str(exc)) from exc


def handle_bad_gateway(_: Request, exc: Exception) -> NoReturn:
    raise BadGatewayException(detail=str(exc)) from exc


domain_exception_handlers = {
    BlockNotFoundError: handle_not_found,
    ExtrinsicNotFoundError: handle_not_found,
    CertificateNotFoundError: handle_not_found,
    CommitmentNotFoundError: handle_not_found,
    RecentObjectMissingError: handle_service_unavailable,
    RecentObjectStaleError: handle_service_unavailable,
    CertificateGenerationFailedError: handle_bad_gateway,
}


__all__ = ["domain_exception_handlers"]
