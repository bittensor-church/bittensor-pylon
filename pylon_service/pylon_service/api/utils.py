import re
from functools import wraps
from inspect import iscoroutinefunction

from litestar import Request, Response
from litestar.exceptions import HTTPException
from litestar.handlers.http_handlers import decorators as http_decorators
from litestar.response import Redirect
from pylon_commons.endpoints import Endpoint

from pylon_service.api.services import (
    BlockNotFoundError,
    CertificateGenerationFailedError,
    CertificateNotFoundError,
    CommitmentNotFoundError,
    ExtrinsicNotFoundError,
    RecentObjectMissingError,
    RecentObjectStaleError,
)
from pylon_service.bittensor.exceptions import BittensorTransportError, RuntimeApiUnavailableException
from pylon_service.evm.exceptions import EvmInvalidAbiError, EvmInvalidAddressError, EvmRpcError
from pylon_service.identities import identities


def _response_for_exception(exc: Exception) -> Response | None:
    if isinstance(exc, (BlockNotFoundError, ExtrinsicNotFoundError, CertificateNotFoundError, CommitmentNotFoundError)):
        return Response(status_code=404, content={"status_code": 404, "detail": str(exc)})

    if isinstance(exc, (RecentObjectMissingError, RecentObjectStaleError)):
        return Response(status_code=503, content={"status_code": 503, "detail": str(exc)})

    if isinstance(exc, CertificateGenerationFailedError):
        return Response(status_code=502, content={"status_code": 502, "detail": str(exc)})

    if isinstance(exc, BittensorTransportError):
        return Response(status_code=502, content={"status_code": 502, "detail": exc.detail})

    if isinstance(exc, RuntimeApiUnavailableException):
        return Response(status_code=501, content={"status_code": 501, "detail": exc.detail})

    if isinstance(exc, EvmInvalidAddressError):
        return Response(status_code=400, content={"status_code": 400, "detail": exc.detail})

    if isinstance(exc, EvmInvalidAbiError):
        return Response(status_code=422, content={"status_code": 422, "detail": exc.detail})

    if isinstance(exc, EvmRpcError):
        return Response(status_code=502, content={"status_code": 502, "detail": exc.detail})

    if isinstance(exc, HTTPException):
        content = {"status_code": exc.status_code, "detail": exc.detail}
        if exc.extra is not None:
            content["extra"] = exc.extra
        return Response(status_code=exc.status_code, content=content, headers=exc.headers)

    return None


async def check_identity_netuid(request: Request) -> Response | None:
    identity_name = request.path_params["identity_name"]
    netuid = request.path_params["netuid"]
    identity = identities.get(identity_name)
    if identity and identity.netuid != netuid:
        correct_path = re.sub(r"/subnet/\d+", f"/subnet/{identity.netuid}", request.url.path, count=1)
        return Redirect(path=correct_path, status_code=308)
    return None


def handler(endpoint: Endpoint, **kwargs):
    """
    Decorator to create litestar handlers using endpoints defined in Endpoint enums.

    It is encouraged to define handlers with Endpoint enums so that Pylon service can share endpoint info
    with Pylon client.
    The decorator automatically sets the proper url, name and method for the endpoint,
    other kwargs may be set by passing them to this decorator.
    """
    method = getattr(http_decorators, endpoint.method.lower())
    name = kwargs.pop("name", endpoint.reverse)

    def decorator(fn):
        if iscoroutinefunction(fn):

            @wraps(fn)
            async def async_wrapped(*args, **inner_kwargs):
                try:
                    return await fn(*args, **inner_kwargs)
                except Exception as exc:
                    response = _response_for_exception(exc)
                    if response is not None:
                        return response
                    raise

            wrapped = async_wrapped

        else:

            @wraps(fn)
            def sync_wrapped(*args, **inner_kwargs):
                try:
                    return fn(*args, **inner_kwargs)
                except Exception as exc:
                    response = _response_for_exception(exc)
                    if response is not None:
                        return response
                    raise

            wrapped = sync_wrapped

        return method(endpoint.url, name=name, **kwargs)(wrapped)

    return decorator
