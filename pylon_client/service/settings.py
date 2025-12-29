from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from pylon_client._internal.common.constants import BLOCK_PROCESSING_TIME
from pylon_client._internal.common.settings import ENV_FILE, Settings
from pylon_client._internal.common.types import NetUid
from pylon_client.service.bittensor.recent import HardLimit, SoftLimit


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
    def update_interval_seconds(self) -> int:
        """
        Calculate the update interval as (soft_limit - refresh_lead) blocks.
        This ensures the cache is updated before reaching the soft limit.
        """
        interval_blocks = max(self.soft_limit_blocks - self.refresh_lead_blocks, 1)
        return interval_blocks * BLOCK_PROCESSING_TIME


recent_objects_settings = RecentObjectsSettings()
settings = Settings()  # type: ignore
