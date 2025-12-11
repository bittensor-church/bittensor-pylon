from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from pylon._internal.common.constants import BLOCK_PROCESSING_TIME
from pylon._internal.common.settings import ENV_FILE
from pylon._internal.common.types import NetUid
from pylon.service.identities import identities


class CacheSettings(BaseSettings):
    recent_neurons_soft_limit: int = 100
    recent_neurons_hard_limit: int = 150
    recent_neurons_netuids: list[NetUid] = Field(default_factory=list)

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_prefix="PYLON_",
        extra="ignore",
    )

    @property
    def all_recent_neurons_netuids(self) -> list[NetUid]:
        identity_netuids = [identity.netuid for identity in identities.values()]

        combined = set(self.recent_neurons_netuids) | set(identity_netuids)
        return list(combined)

    @property
    def recent_neurons_update_task_interval(self) -> float:
        # Let's divide the hard limit by 2 and take whichever is smaller from the result and soft limit.
        # Set the interval to 10 blocks behind the result of the above step.
        # It'll 1) give us 120 seconds to update the cache before the soft limit, and 2) add two update passes
        # before the hard limit is reached.
        max_limit = min(self.recent_neurons_hard_limit // 2, self.recent_neurons_soft_limit)
        min_limit = max(max_limit - 10, 1)  # can't go below 1
        return min_limit * BLOCK_PROCESSING_TIME


settings = CacheSettings()
