from litestar import Request, Response

from pylon_service.bittensor.exceptions import ArchiveFallbackException
from pylon_service.exceptions import BadGatewayException


def archive_fallback_handler(_: Request, exc: ArchiveFallbackException) -> Response:
    raise BadGatewayException(detail=exc.detail)
