from typing import Self

from litestar.config.response_cache import ResponseCacheConfig
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

# Default cache config. Only used for endpoints with explicit @handler(..., cache=...)
response_cache_config = ResponseCacheConfig()
