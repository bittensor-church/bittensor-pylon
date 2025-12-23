from litestar import Litestar
from litestar.di import Provide
from litestar.openapi.config import OpenAPIConfig
from litestar.plugins.prometheus import PrometheusConfig

from pylon_client.service import dependencies, lifespans
from pylon_client.service.prometheus_controller import AuthenticatedPrometheusController
from pylon_client.service.routers import v1_router
from pylon_client.service.schema import PylonSchemaPlugin
from pylon_client.service.sentry_config import init_sentry
from pylon_client.service.settings import settings
from pylon_client.service.stores import stores


def create_app() -> Litestar:
    """Create a Litestar app"""
    # Configure Prometheus
    prometheus_config = PrometheusConfig(
        app_name="bittensor-pylon",
        prefix="pylon",
        group_path=True,  # Group metrics by path template to avoid cardinality explosion
    )

    return Litestar(
        route_handlers=[
            v1_router,
            AuthenticatedPrometheusController,
        ],
        openapi_config=OpenAPIConfig(
            title="Bittensor Pylon API",
            version="0.1.0",
            description="REST API for the bittensor-pylon service",
        ),
        middleware=[prometheus_config.middleware],
        lifespan=[lifespans.bittensor_client_pool, lifespans.scheduler_lifespan],
        dependencies={"bt_client_pool": Provide(dependencies.bt_client_pool_dep, use_cache=True)},
        plugins=[PylonSchemaPlugin()],
        stores=stores,
        debug=settings.debug,
    )


init_sentry()
app = create_app()
