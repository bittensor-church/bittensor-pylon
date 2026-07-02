import os
from collections.abc import Iterable
from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .types import (
    ArchiveBlocksCutoff,
    BittensorNetwork,
    IdentityName,
)
from .types import evm as evm_types

ENV_FILE = os.environ.get("PYLON_ENV_FILE", ".env")

# Pairs of (main, archive) network settings that must be overridden together.
_PAIRED_NETWORK_FIELDS: tuple[tuple[str, str], ...] = (
    ("bittensor_network", "bittensor_archive_network"),
    ("evm_rpc_url", "evm_archive_rpc_url"),
)


def _validate_paired_settings_overridden_together(
    fields_set: set[str],
    field_pairs: Iterable[tuple[str, str]],
    env_prefix: str,
) -> None:
    """
    Ensure each setting pair is either both left at its default or both set explicitly.

    A pair with exactly one member provided is rejected, because silently mixing an overridden
    value with a defaulted counterpart is an easy and dangerous misconfiguration. Repeating the
    default value is allowed, as long as it is provided explicitly.

    Raises:
        ValueError: If exactly one member of a pair was provided.
    """
    for main_field, archive_field in field_pairs:
        main_set = main_field in fields_set
        archive_set = archive_field in fields_set
        if main_set == archive_set:
            continue
        provided, missing = (main_field, archive_field) if main_set else (archive_field, main_field)
        raise ValueError(
            f"{env_prefix}{provided.upper()} was overridden but {env_prefix}{missing.upper()} was left "
            f"at its default. Set both explicitly (you may repeat the default value, but it must be explicit)."
        )


class Settings(BaseSettings):
    # bittensor
    bittensor_network: BittensorNetwork = BittensorNetwork("finney")
    bittensor_archive_network: BittensorNetwork = BittensorNetwork("archive")
    bittensor_archive_blocks_cutoff: ArchiveBlocksCutoff = ArchiveBlocksCutoff(300)
    bittensor_wallet_path: str = "/root/.bittensor/wallets"

    # Identities and access
    identities: list[IdentityName] = Field(default_factory=list)
    open_access_token: str = ""

    # metrics
    metrics_token: str = ""

    # docker
    docker_image_name: str = "bittensor_pylon"

    # block duration in seconds (used for drand reveal round calculation)
    block_duration_seconds: float = Field(default=12.0, gt=0)

    # commit-reveal cycle
    commit_cycle_length: int = 3  # Number of tempos to wait between weight commitments
    commit_window_start_offset: int = 180  # Offset from interval start to begin commit window
    commit_window_end_buffer: int = 10  # Buffer at the end of commit window before interval ends

    # weights endpoint behaviour
    weights_retry_attempts: int = 200
    weights_retry_delay_seconds: int = 1

    # commitment endpoint behaviour
    commitment_retry_attempts: int = 10
    commitment_retry_delay_seconds: int = 1

    # deployment environment (single source of truth for Sentry and OTEL)
    environment: str = "production"

    # request timeouts
    default_request_timeout_seconds: float = 60.0
    max_request_timeout_seconds: float = 300.0

    # evm
    # WARNING: these URLs are recorded as-is in telemetry (OpenTelemetry spans, debug logs, and the
    # Prometheus `rpc_url` metric label), so do NOT embed credentials in them (no `user:pass@` and no
    # path/query API keys like `/v2/<key>`). If a provider requires authentication, pass it out of band.
    evm_rpc_url: evm_types.RpcUrl = evm_types.RpcUrl("https://lite.chain.opentensor.ai")
    evm_archive_rpc_url: evm_types.RpcUrl = evm_types.RpcUrl("https://archive.chain.opentensor.ai")
    evm_archive_blocks_cutoff: ArchiveBlocksCutoff = ArchiveBlocksCutoff(300)

    # debug
    debug: bool = False

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", env_prefix="PYLON_", extra="ignore")

    @model_validator(mode="after")
    def validate_networks_overridden_together(self) -> Self:
        """
        Reject overriding only one network of a main/archive pair, leaving its counterpart on the default.
        """
        _validate_paired_settings_overridden_together(
            self.model_fields_set,
            _PAIRED_NETWORK_FIELDS,
            self.model_config.get("env_prefix", "") or "",
        )
        return self
