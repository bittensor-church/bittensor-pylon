from enum import nonmember, unique
from http import HTTPMethod

from pylon_commons.apiver import ApiVersion
from pylon_commons.endpoints import Endpoint as BaseEndpoint


@unique
class Endpoint(BaseEndpoint):
    _version = nonmember(ApiVersion.UNSTABLE)  # type: ignore[reportAssignmentType]

    LATEST_COMMITMENTS = (HTTPMethod.GET, "/block/latest/commitments", "latest_commitments_unstable")
