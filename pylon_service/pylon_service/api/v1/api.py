from litestar import Controller, Response, status_codes
from litestar.di import Provide
from pylon_commons.models import Hotkey
from pylon_commons.types import NetUid
from pylon_commons.v1.bodies import SetWeightsBody
from pylon_commons.v1.endpoints import Endpoint
from pylon_commons.v1.responses import (
    GetCommitmentResponse,
    GetCommitmentsResponse,
)

from pylon_service.api._unstable.api import (
    BaseController as UnstableBaseController,
)
from pylon_service.api._unstable.api import (
    get_extrinsic_endpoint,
    get_identities,
    get_latest_block_info_endpoint,
)
from pylon_service.api.utils import check_identity_netuid, handler
from pylon_service.bittensor.contact_router import BittensorContactRouter
from pylon_service.dependencies import (
    bt_contact_router_identity_dep,
    bt_contact_router_open_access_dep,
    identity_dep,
    recent_object_provider_identity_dep,
    recent_object_provider_open_access_dep,
)
from pylon_service.guards import identity_auth_guard, open_access_auth_guard

from .services import CommitmentService, WeightService


class BaseController:
    @handler(Endpoint.LATEST_COMMITMENTS)
    async def get_commitments_endpoint(
        self, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> GetCommitmentsResponse:
        block, commitments = await CommitmentService.get_commitments(bt_contact_router, netuid)
        return GetCommitmentsResponse(block=block, commitments=commitments)

    @handler(Endpoint.LATEST_COMMITMENTS_HOTKEY)
    async def get_commitment_endpoint(
        self, hotkey: Hotkey, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> GetCommitmentResponse:
        block, commitment = await CommitmentService.get_commitment(bt_contact_router, netuid, hotkey)
        return GetCommitmentResponse(block=block, **commitment.model_dump())

    @handler(Endpoint.LATEST_COMMITMENTS_SELF)
    async def get_own_commitment_endpoint(
        self, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> GetCommitmentResponse:
        block, commitment = await CommitmentService.get_own_commitment(bt_contact_router, netuid)
        return GetCommitmentResponse(block=block, **commitment.model_dump())

    @handler(Endpoint.SUBNET_WEIGHTS)
    async def put_weights_endpoint(
        self, data: SetWeightsBody, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> Response:
        await WeightService.set_weights(bt_contact_router, netuid, data.weights)
        return Response(
            {"detail": "weights update scheduled", "count": len(data.weights)}, status_code=status_codes.HTTP_200_OK
        )


class OpenAccessController(Controller):
    path = "/subnet/{netuid:int}/"
    guards = [open_access_auth_guard]
    dependencies = {
        "bt_contact_router": Provide(bt_contact_router_open_access_dep),
        "recent_object_provider": Provide(recent_object_provider_open_access_dep),
    }

    get_commitments_endpoint = BaseController.get_commitments_endpoint
    get_commitment_endpoint = BaseController.get_commitment_endpoint

    get_neurons = UnstableBaseController.get_neurons
    get_latest_neurons = UnstableBaseController.get_latest_neurons
    get_recent_neurons = UnstableBaseController.get_recent_neurons
    get_validators = UnstableBaseController.get_validators
    get_latest_validators = UnstableBaseController.get_latest_validators
    get_certificates_endpoint = UnstableBaseController.get_certificates_endpoint
    get_certificate_endpoint = UnstableBaseController.get_certificate_endpoint


class IdentityController(Controller):
    path = "/identity/{identity_name:str}/subnet/{netuid:int}"
    guards = [identity_auth_guard]
    before_request = check_identity_netuid
    dependencies = {
        "identity": Provide(identity_dep),
        "bt_contact_router": Provide(bt_contact_router_identity_dep),
        "recent_object_provider": Provide(recent_object_provider_identity_dep),
    }

    get_commitments_endpoint = BaseController.get_commitments_endpoint
    get_commitment_endpoint = BaseController.get_commitment_endpoint
    get_own_commitment_endpoint = BaseController.get_own_commitment_endpoint
    put_weights_endpoint = BaseController.put_weights_endpoint

    get_neurons = UnstableBaseController.get_neurons
    get_latest_neurons = UnstableBaseController.get_latest_neurons
    get_recent_neurons = UnstableBaseController.get_recent_neurons
    get_validators = UnstableBaseController.get_validators
    get_latest_validators = UnstableBaseController.get_latest_validators
    get_certificates_endpoint = UnstableBaseController.get_certificates_endpoint
    get_certificate_endpoint = UnstableBaseController.get_certificate_endpoint
    get_own_certificate_endpoint = UnstableBaseController.get_own_certificate_endpoint
    generate_certificate_keypair_endpoint = UnstableBaseController.generate_certificate_keypair_endpoint
    set_commitment_endpoint = UnstableBaseController.set_commitment_endpoint


__all__ = [
    "OpenAccessController",
    "IdentityController",
    "get_identities",
    "get_extrinsic_endpoint",
    "get_latest_block_info_endpoint",
]
