from pathlib import Path
from typing import Generic, TypeVar

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from tenacity import AsyncRetrying, Retrying

from pylon_client._internal.pylon_commons.timeout import PylonTimeout
from pylon_client._internal.pylon_commons.types import IdentityName, PylonAuthToken

RetryT = TypeVar("RetryT", bound=AsyncRetrying | Retrying)


class BaseConfig(BaseSettings, Generic[RetryT]):
    """
    Base configuration for Pylon clients.

    Any field can be set explicitly or fall back to a ``PYLON_CLIENT_<FIELD>`` variable from the
    process environment (e.g. ``PYLON_CLIENT_NEURONS_FILE``); explicitly passed values take precedence.

    Args:
        address (required): The Pylon service address.
        identity_name: The name of the identity to use.
        identity_token: Token to use for authentication into chosen identity.
        open_access_token: Token to use for authentication into open access api.
        retry: Configuration of retrying in case of a failed request.
        timeout: Timeout configuration for requests.
        mtls_cert_path: Path to the client TLS certificate file used for mTLS when calling get_neuron_client.
            Must be provided together with mtls_key_path.
        mtls_key_path: Path to the client TLS private key file used for mTLS when calling get_neuron_client.
            Must be provided together with mtls_cert_path.
    """

    model_config = SettingsConfigDict(
        env_prefix="PYLON_CLIENT_", env_nested_delimiter="__", extra="ignore", arbitrary_types_allowed=True
    )

    address: str
    identity_name: IdentityName | None = None
    identity_token: PylonAuthToken | None = None
    open_access_token: PylonAuthToken | None = None
    retry: RetryT
    timeout: PylonTimeout = PylonTimeout()
    mtls_cert_path: str | None = None
    mtls_key_path: str | None = None

    def model_post_init(self, context) -> None:
        self.retry.reraise = True

    @model_validator(mode="after")
    def validate_identity(self):
        if bool(self.identity_name) != bool(self.identity_token):
            raise ValueError("Identity name must be provided in pair with identity token.")
        return self

    @model_validator(mode="after")
    def validate_cert(self):
        if bool(self.mtls_cert_path) != bool(self.mtls_key_path):
            raise ValueError("mtls_cert_path and mtls_key_path must be provided together.")
        if self.mtls_cert_path and not Path(self.mtls_cert_path).exists():
            raise ValueError(f"mtls_cert_path not found: {self.mtls_cert_path!r}")
        if self.mtls_key_path and not Path(self.mtls_key_path).exists():
            raise ValueError(f"mtls_key_path not found: {self.mtls_key_path!r}")
        return self
