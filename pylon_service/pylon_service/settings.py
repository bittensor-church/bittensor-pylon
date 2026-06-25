import uuid
from typing import Self

from litestar.config.response_cache import ResponseCacheConfig
from opentelemetry.semconv.attributes import deployment_attributes, service_attributes
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pylon_commons.settings import ENV_FILE, Settings
from pylon_commons.types import NetUid

from pylon_service.bittensor.recent import HardLimit, SoftLimit

settings = Settings()  # type: ignore


class DatabaseSettings(BaseSettings):
    """
    Settings for the database.
    """

    path: str | None = None

    def get_url(self, async_db: bool = True) -> str:
        db_path = self.path if self.path else "./pylon.db"

        return f"sqlite{'+aiosqlite' if async_db else ''}:///{db_path}"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_prefix="PYLON_DATABASE_",
        extra="ignore",
    )


database_settings = DatabaseSettings()


class RecentObjectsSettings(BaseSettings):
    """
    Settings for the recent object caching system.
    """

    soft_limit_blocks: SoftLimit = SoftLimit(100)
    hard_limit_blocks: HardLimit = HardLimit(150)
    refresh_lead_blocks: int = 10
    netuids: list[NetUid] = Field(default_factory=list)

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_prefix="PYLON_RECENT_OBJECTS_",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_hard_limit(self) -> Self:
        if self.soft_limit_blocks > self.hard_limit_blocks:
            raise ValueError("hard_limit_blocks must be greater than soft_limit_blocks.")
        return self

    @property
    def update_interval_seconds(self) -> float:
        """
        Calculate the update interval as (soft_limit - refresh_lead) blocks.
        This ensures the cache is updated before reaching the soft limit.
        """
        interval_blocks = max(self.soft_limit_blocks - self.refresh_lead_blocks, 1)
        return interval_blocks * settings.block_duration_seconds


recent_objects_settings = RecentObjectsSettings()


_DEFAULT_SERVICE_INSTANCE_ID = str(uuid.uuid4())


class OtelSettings(BaseSettings):
    """OpenTelemetry resource attributes injected into every log line."""

    service_namespace: str = "bittensor-pylon"
    service_name: str = "pylon_service"
    deployment_environment: str = Field(default_factory=lambda: settings.environment)
    service_instance_id: str = _DEFAULT_SERVICE_INSTANCE_ID
    service_version: str = ""
    collector_endpoint: str = ""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_prefix="PYLON_OTEL_",
        extra="ignore",
    )

    @property
    def normalized_collector_endpoint(self) -> str:
        """
        Return the collector endpoint with surrounding whitespace and trailing slashes removed,
        so signal paths can be appended without producing a double slash.
        """
        return self.collector_endpoint.strip().rstrip("/")

    @property
    def traces_enabled(self) -> bool:
        """
        Return whether traces export is enabled (a non-empty endpoint is configured).
        """
        return bool(self.normalized_collector_endpoint)

    def resource_attributes(self) -> dict[str, str]:
        """Return OTEL resource attributes as dotted-key fields for log injection."""
        attrs = {
            service_attributes.SERVICE_NAMESPACE: self.service_namespace,
            service_attributes.SERVICE_NAME: self.service_name,
            deployment_attributes.DEPLOYMENT_ENVIRONMENT_NAME: self.deployment_environment,
            service_attributes.SERVICE_INSTANCE_ID: self.service_instance_id,
        }
        if self.service_version:
            attrs[service_attributes.SERVICE_VERSION] = self.service_version
        return attrs


otel_settings = OtelSettings()


class SentrySettings(BaseSettings):
    """Settings for Sentry error tracking."""

    dsn: str = ""
    environment: str = Field(default_factory=lambda: settings.environment)

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_prefix="PYLON_SENTRY_",
        extra="ignore",
    )


sentry_settings = SentrySettings()

# Default cache config. Only used for endpoints with explicit @handler(..., cache=...)
response_cache_config = ResponseCacheConfig()
