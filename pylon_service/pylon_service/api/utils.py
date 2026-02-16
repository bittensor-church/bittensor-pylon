from litestar.handlers.http_handlers import decorators as http_decorators
from pylon_commons.endpoints import Endpoint


def handler(endpoint: Endpoint, **kwargs):
    """
    Decorator to create litestar handlers using endpoints defined in Endpoint enums.

    It is encouraged to define handlers with Endpoint enums so that Pylon service can share endpoint info
    with Pylon client.
    The decorator automatically sets the proper url, name and method for the endpoint,
    other kwargs may be set by passing them to this decorator.
    """
    method = getattr(http_decorators, endpoint.method.lower())
    return method(endpoint.url, name=endpoint.reverse, **kwargs)
