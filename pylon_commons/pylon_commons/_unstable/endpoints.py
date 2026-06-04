from enum import nonmember, unique
from http import HTTPMethod

from ..apiver import ApiVersion
from ..endpoints import Endpoint as BaseEndpoint
from ..types import IdentityName, NetUid


@unique
class Endpoint(BaseEndpoint):
    """
    Unstable API endpoint path definitions.

    This is the canonical set of all endpoint members. v1/endpoints.py
    duplicates these with a _v1 suffix on reverse names.

    IMPORTANT: Each route handler must have its own unique enum member.
    Even if multiple handlers share the same path (e.g., different HTTP methods),
    they must have separate enum members to ensure unique reverse names in Litestar.
    """

    _version = nonmember(ApiVersion.UNSTABLE)  # type: ignore[reportAssignmentType]

    CERTIFICATES = (HTTPMethod.GET, "/block/latest/certificates", "certificates")
    CERTIFICATES_GENERATE = (HTTPMethod.POST, "/certificates/self", "certificates_generate")
    CERTIFICATES_HOTKEY = (HTTPMethod.GET, "/block/latest/certificates/{hotkey:str}", "certificates_hotkey")
    CERTIFICATES_SELF = (HTTPMethod.GET, "/block/latest/certificates/self", "certificates_self")
    COMMITMENTS = (HTTPMethod.POST, "/commitments", "commitments")
    REVEALED_COMMITMENTS = (HTTPMethod.POST, "/commitments/revealed", "revealed_commitments")
    EXTRINSIC = (HTTPMethod.GET, "/block/{block_number:int}/extrinsic/{extrinsic_index:int}", "extrinsic")
    IDENTITIES = (HTTPMethod.GET, "/identities", "identities")
    DRAND_LAST_STORED_ROUND = (HTTPMethod.GET, "/block/latest/drand/last_stored_round", "drand_last_stored_round")
    LATEST_BLOCK_INFO = (HTTPMethod.GET, "/block/latest", "latest_block_info")
    LATEST_COMMITMENTS = (HTTPMethod.GET, "/block/latest/commitments", "latest_commitments")
    LATEST_COMMITMENTS_REVEALED = (HTTPMethod.GET, "/block/latest/commitments/revealed", "latest_commitments_revealed")
    LATEST_COMMITMENTS_HOTKEY = (HTTPMethod.GET, "/block/latest/commitments/{hotkey:str}", "latest_commitments_hotkey")
    LATEST_COMMITMENTS_REVEALED_HOTKEY = (
        HTTPMethod.GET,
        "/block/latest/commitments/revealed/{hotkey:str}",
        "latest_commitments_revealed_hotkey",
    )
    LATEST_COMMITMENTS_SELF = (HTTPMethod.GET, "/block/latest/commitments/self", "latest_commitments_self")
    LATEST_COMMITMENTS_REVEALED_SELF = (
        HTTPMethod.GET,
        "/block/latest/commitments/revealed/self",
        "latest_commitments_revealed_self",
    )
    EVM_LOGS = (HTTPMethod.POST, "/evm/contracts/{contract_address:str}/logs", "evm_logs")
    LATEST_NEURONS = (HTTPMethod.GET, "/block/latest/neurons", "latest_neurons")
    LATEST_VALIDATORS = (HTTPMethod.GET, "/block/latest/validators", "latest_validators")
    NEURONS = (HTTPMethod.GET, "/block/{block_number:int}/neurons", "neurons")
    RECENT_NEURONS = (HTTPMethod.GET, "/block/recent/neurons", "recent_neurons")
    LATEST_PRICES = (HTTPMethod.GET, "/block/latest/prices", "latest_prices")
    PRICES = (HTTPMethod.GET, "/block/{block_number:int}/prices", "prices")
    SUBNET_LATEST_PRICE = (HTTPMethod.GET, "/block/latest/price", "subnet_latest_price")
    SUBNET_PRICE = (HTTPMethod.GET, "/block/{block_number:int}/price", "subnet_price")
    SUBNET_WEIGHTS = (HTTPMethod.PUT, "/weights", "subnet_weights")
    SUBNET_MECHANISM_WEIGHTS = (HTTPMethod.PUT, "/mechanism/{mechanism_id:int}/weights", "subnet_mechanism_weights")
    SUBNET_MECHANISM_WEIGHTS_STATUS = (
        HTTPMethod.GET,
        "/mechanism/{mechanism_id:int}/block/{block_number:int}/weights/status",
        "subnet_mechanism_weight_status",
    )
    VALIDATORS = (HTTPMethod.GET, "/block/{block_number:int}/validators", "validators")
    LATEST_EVM_ASSOCIATIONS = (HTTPMethod.GET, "/block/latest/evm_associations", "latest_evm_associations")

    def absolute_url(self, netuid_: NetUid | None = None, identity_name_: IdentityName | None = None, **kwargs):
        formatted_endpoint = self.format_url(**kwargs)
        netuid_part = f"/subnet/{netuid_}" if netuid_ is not None else ""
        identity_part = f"/identity/{identity_name_}" if identity_name_ is not None else ""
        open_access_part = "/openaccess" if identity_name_ is None else ""
        return f"{self._version.prefix}{identity_part}{open_access_part}{netuid_part}{formatted_endpoint}"
