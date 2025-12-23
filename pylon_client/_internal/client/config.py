from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, model_validator
from tenacity import AsyncRetrying, Retrying

from pylon_client._internal.common.types import IdentityName, PylonAuthToken

RetryT = TypeVar("RetryT", bound=AsyncRetrying | Retrying)


class BaseConfig(BaseModel, Generic[RetryT]):
    """
    Base configuration for Pylon clients.

    Args:
        address (required): The Pylon service address.
        identity_name: The name of the identity to use.
        identity_token: Token to use for authentication into chosen identity.
        open_access_token: Token to use for authentication into open access api.
        retry: Configuration of retrying in case of a failed request.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    address: str
    identity_name: IdentityName | None = None
    identity_token: PylonAuthToken | None = None
    open_access_token: PylonAuthToken | None = None
    retry: RetryT

    def model_post_init(self, context) -> None:
        self.retry.reraise = True

    @model_validator(mode="after")
    def validate_identity(self):
        if bool(self.identity_name) != bool(self.identity_token):
            raise ValueError("Identity name must be provided in pair with identity token.")
        return self
