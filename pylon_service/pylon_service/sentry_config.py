import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.litestar import LitestarIntegration

from pylon_service.settings import sentry_settings


def init_sentry() -> None:
    """Initialize Sentry if DSN is configured."""
    if not sentry_settings.dsn:
        return

    sentry_sdk.init(
        dsn=sentry_settings.dsn,
        environment=sentry_settings.environment,
        integrations=[
            LitestarIntegration(),
            AsyncioIntegration(),
        ],
    )
