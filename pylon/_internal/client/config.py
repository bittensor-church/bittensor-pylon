from pydantic import BaseModel, ConfigDict, model_validator
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from pylon._internal.common.exceptions import PylonRequestException
from pylon._internal.common.types import IdentityName, PylonAuthToken

DEFAULT_RETRIES = AsyncRetrying(
    wait=wait_exponential_jitter(initial=0.1, jitter=0.2),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(PylonRequestException),
)


class AsyncConfig(BaseModel):
    """
    Configuration for the asynchronous Pylon clients.

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
    retry: AsyncRetrying = DEFAULT_RETRIES.copy()

    def model_post_init(self, context) -> None:
        # Force reraise to ensure proper error handling in the client.
        self.retry.reraise = True

    @model_validator(mode="after")
    def validate_identity(self):
        if bool(self.identity_name) != bool(self.identity_token):
            raise ValueError("Identity name must be provided in pair with identity token.")
        return self
