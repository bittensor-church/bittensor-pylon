from pylon_client._internal.api._unstable.asynchronous.api import AsyncIdentityApi as UnstableAsyncIdentityApi
from pylon_client._internal.api._unstable.asynchronous.api import AsyncOpenAccessApi as UnstableAsyncOpenAccessApi
from pylon_client._internal.pylon_commons.apiver import ApiVersion
from pylon_client._internal.pylon_commons.types import NetUid
from pylon_client._internal.pylon_commons.v1.requests import GetCommitmentsRequest


class AsyncOpenAccessApi(UnstableAsyncOpenAccessApi):
    api_version = ApiVersion.V1

    async def _get_commitments_request(self, netuid: NetUid) -> GetCommitmentsRequest:  # type: ignore[reportIncompatibleMethodOverride]
        return GetCommitmentsRequest(netuid=netuid)


class AsyncIdentityApi(UnstableAsyncIdentityApi):
    api_version = ApiVersion.V1

    async def _get_commitments_request(self) -> GetCommitmentsRequest:  # type: ignore[reportIncompatibleMethodOverride]
        assert self._login_response, "Attempted api request without authentication."
        return GetCommitmentsRequest(
            netuid=self._login_response.netuid,
            identity_name=self._login_response.identity_name,
        )
