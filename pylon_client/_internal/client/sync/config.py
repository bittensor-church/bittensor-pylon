from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from pylon_client._internal.client.config import BaseConfig
from pylon_client._internal.common.exceptions import PylonRequestException

DEFAULT_RETRIES = Retrying(
    wait=wait_exponential_jitter(initial=0.1, jitter=0.2),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(PylonRequestException),
)


class Config(BaseConfig[Retrying]):
    """
    Configuration for the synchronous Pylon clients.

    Args:
        address (required): The Pylon service address.
        identity_name: The name of the identity to use.
        identity_token: Token to use for authentication into chosen identity.
        open_access_token: Token to use for authentication into open access api.
        retry: Configuration of retrying in case of a failed request.
    """

    retry: Retrying = DEFAULT_RETRIES.copy()
