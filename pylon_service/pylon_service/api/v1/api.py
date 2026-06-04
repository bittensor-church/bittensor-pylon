from litestar import Controller, Response, status_codes
from pylon_commons.models import Hotkey
from pylon_commons.types import NetUid
from pylon_commons.v1.bodies import SetWeightsBody
from pylon_commons.v1.endpoints import Endpoint
from pylon_commons.v1.responses import (
    GetCommitmentResponse,
    GetCommitmentsResponse,
)

from pylon_service.api._unstable.api import (
    Handlers as UnstableHandlers,
)
from pylon_service.api.utils import check_identity_netuid, handler
from pylon_service.dependencies import (
    IDENTITY_PROVIDERS,
    OPEN_ACCESS_SUBNET_PROVIDERS,
    PUBLIC_PROVIDERS,
)
from pylon_service.guards import identity_auth_guard, open_access_auth_guard

from .services import CommitmentService, WeightService


class Handlers:
    @handler(Endpoint.LATEST_COMMITMENTS)
    async def get_commitments_endpoint(
        self, v1_commitment_service: CommitmentService, netuid: NetUid
    ) -> GetCommitmentsResponse:
        block, commitments = await v1_commitment_service.get_commitments(netuid)
        return GetCommitmentsResponse(block=block, commitments=commitments)

    @handler(Endpoint.LATEST_COMMITMENTS_HOTKEY)
    async def get_commitment_endpoint(
        self, hotkey: Hotkey, v1_commitment_service: CommitmentService, netuid: NetUid
    ) -> GetCommitmentResponse:
        block, commitment = await v1_commitment_service.get_commitment(netuid, hotkey)
        return GetCommitmentResponse(block=block, **commitment.model_dump())

    @handler(Endpoint.LATEST_COMMITMENTS_SELF)
    async def get_own_commitment_endpoint(
        self, v1_commitment_service: CommitmentService, netuid: NetUid
    ) -> GetCommitmentResponse:
        block, commitment = await v1_commitment_service.get_own_commitment(netuid)
        return GetCommitmentResponse(block=block, **commitment.model_dump())

    @handler(Endpoint.SUBNET_WEIGHTS)
    async def put_weights_endpoint(
        self, data: SetWeightsBody, v1_weight_service: WeightService, netuid: NetUid
    ) -> Response:
        await v1_weight_service.set_weights(netuid, data.weights)
        return Response(
            {"detail": "weights update scheduled", "count": len(data.weights)}, status_code=status_codes.HTTP_200_OK
        )


class PublicController(Controller):
    dependencies = PUBLIC_PROVIDERS

    get_identities = UnstableHandlers.get_identities
    get_latest_block_info_endpoint = UnstableHandlers.get_latest_block_info_endpoint
    get_extrinsic_endpoint = UnstableHandlers.get_extrinsic_endpoint


class OpenAccessController(Controller):
    path = "/subnet/{netuid:int}/"
    guards = [open_access_auth_guard]
    dependencies = OPEN_ACCESS_SUBNET_PROVIDERS

    get_commitments_endpoint = Handlers.get_commitments_endpoint
    get_commitment_endpoint = Handlers.get_commitment_endpoint

    get_neurons = UnstableHandlers.get_neurons
    get_latest_neurons = UnstableHandlers.get_latest_neurons
    get_recent_neurons = UnstableHandlers.get_recent_neurons
    get_validators = UnstableHandlers.get_validators
    get_latest_validators = UnstableHandlers.get_latest_validators
    get_certificates_endpoint = UnstableHandlers.get_certificates_endpoint
    get_certificate_endpoint = UnstableHandlers.get_certificate_endpoint


class IdentityController(Controller):
    path = "/identity/{identity_name:str}/subnet/{netuid:int}"
    guards = [identity_auth_guard]
    before_request = check_identity_netuid
    dependencies = IDENTITY_PROVIDERS

    get_commitments_endpoint = Handlers.get_commitments_endpoint
    get_commitment_endpoint = Handlers.get_commitment_endpoint
    get_own_commitment_endpoint = Handlers.get_own_commitment_endpoint
    put_weights_endpoint = Handlers.put_weights_endpoint

    get_neurons = UnstableHandlers.get_neurons
    get_latest_neurons = UnstableHandlers.get_latest_neurons
    get_recent_neurons = UnstableHandlers.get_recent_neurons
    get_validators = UnstableHandlers.get_validators
    get_latest_validators = UnstableHandlers.get_latest_validators
    get_certificates_endpoint = UnstableHandlers.get_certificates_endpoint
    get_certificate_endpoint = UnstableHandlers.get_certificate_endpoint
    get_own_certificate_endpoint = UnstableHandlers.get_own_certificate_endpoint
    generate_certificate_keypair_endpoint = UnstableHandlers.generate_certificate_keypair_endpoint
    set_commitment_endpoint = UnstableHandlers.set_commitment_endpoint


__all__ = [
    "PublicController",
    "OpenAccessController",
    "IdentityController",
]
