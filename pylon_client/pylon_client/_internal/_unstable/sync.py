from functools import partial

from pylon_client._internal.pylon_commons._unstable.requests import GetCommitmentsRequestUnstable
from pylon_client._internal.pylon_commons._unstable.responses import GetCommitmentsResponseUnstable
from pylon_client._internal.pylon_commons.types import NetUid
from pylon_client._internal.sync.api import IdentityApi, OpenAccessApi


class OpenAccessApiUnstable:
    """
    Unstable Open access API providing enhanced endpoints with richer data.

    This API contains only methods that have unstable versions with different response formats.
    For the full API, use the standard open_access API.
    """

    def __init__(self, v1_api: OpenAccessApi):
        self._v1_api = v1_api

    def get_commitments(self, netuid: NetUid) -> GetCommitmentsResponseUnstable:
        """
        Retrieves all commitments for a specific subnet at the latest available block.

        Returns commitment data including commitment_block_number for each hotkey.

        Args:
            netuid: The unique identifier of the subnet.

        Returns:
            GetCommitmentsResponseUnstable: containing commitments data mapping hotkeys to Commitment objects.
        """
        return self._v1_api._send_authenticated_request(partial(self._get_commitments_request, netuid))

    def _get_commitments_request(self, netuid: NetUid) -> GetCommitmentsRequestUnstable:
        return GetCommitmentsRequestUnstable(netuid=netuid)


class IdentityApiUnstable:
    """
    Unstable Identity API providing enhanced endpoints with richer data.

    This API contains only methods that have unstable versions with different response formats.
    For the full API, use the standard identity API.
    """

    def __init__(self, v1_api: IdentityApi):
        self._v1_api = v1_api

    def get_commitments(self) -> GetCommitmentsResponseUnstable:
        """
        Retrieves all commitments for the authenticated identity's subnet at the latest available block.

        Returns commitment data including commitment_block_number for each hotkey.

        Returns:
            GetCommitmentsResponseUnstable: containing commitments data mapping hotkeys to Commitment objects.
        """
        return self._v1_api._send_authenticated_request(self._get_commitments_request)

    def _get_commitments_request(self) -> GetCommitmentsRequestUnstable:
        assert self._v1_api._login_response, "Attempted api request without authentication."
        return GetCommitmentsRequestUnstable(
            netuid=self._v1_api._login_response.netuid,
            identity_name=self._v1_api._login_response.identity_name,
        )


class UnstableNamespace:
    """
    Unstable API namespace containing only endpoints that have unstable versions.

    Methods available in this namespace return richer data formats compared to v1.
    This is self-documenting: if a method exists here, it has an unstable version.
    """

    def __init__(self, open_access_api: OpenAccessApi, identity_api: IdentityApi):
        self.open_access = OpenAccessApiUnstable(open_access_api)
        self.identity = IdentityApiUnstable(identity_api)
