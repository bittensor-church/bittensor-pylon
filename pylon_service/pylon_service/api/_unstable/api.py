import logging

from litestar import Controller, Response, status_codes
from litestar.di import Provide
from pylon_commons._unstable.bodies import SetCommitmentBody, SetRevealedCommitmentBody, SetWeightsBody
from pylon_commons._unstable.endpoints import Endpoint
from pylon_commons._unstable.requests import GenerateCertificateKeypairRequest
from pylon_commons._unstable.responses import (
    GetAllRevealedCommitmentsResponse,
    GetCommitmentResponse,
    GetCommitmentsResponse,
    GetDrandLastStoredRoundResponse,
    GetExtrinsicResponse,
    GetIdentitiesResponse,
    GetLatestBlockInfoResponse,
    GetNeuronsResponse,
    GetRevealedCommitmentsResponse,
    GetValidatorsResponse,
    SetRevealedCommitmentResponse,
)
from pylon_commons.models import Hotkey, NeuronCertificate
from pylon_commons.types import BlockNumber, ExtrinsicIndex, MechanismId, NetUid

from pylon_service.api._unstable.services import (
    BlockService,
    CertificateService,
    CommitmentService,
    NeuronService,
    WeightService,
)
from pylon_service.api.utils import check_identity_netuid, handler
from pylon_service.bittensor.contact_router import BittensorContactRouter
from pylon_service.bittensor.recent import RecentObjectProvider
from pylon_service.dependencies import (
    bt_contact_router_identity_dep,
    bt_contact_router_open_access_dep,
    identity_dep,
    recent_object_provider_identity_dep,
    recent_object_provider_open_access_dep,
)
from pylon_service.guards import identity_auth_guard, open_access_auth_guard
from pylon_service.identities import identities

logger = logging.getLogger(__name__)


@handler(
    Endpoint.IDENTITIES,
    status_code=status_codes.HTTP_200_OK,
)
async def get_identities() -> GetIdentitiesResponse:
    return GetIdentitiesResponse(identities={name: identity.netuid for name, identity in identities.items()})


@handler(
    Endpoint.LATEST_BLOCK_INFO,
    cache=3,
    dependencies={"bt_contact_router": Provide(bt_contact_router_open_access_dep)},
)
async def get_latest_block_info_endpoint(bt_contact_router: BittensorContactRouter) -> GetLatestBlockInfoResponse:
    block_info = await BlockService.get_latest_block_info(bt_contact_router)
    return GetLatestBlockInfoResponse.model_validate(block_info, from_attributes=True)


@handler(
    Endpoint.EXTRINSIC,
    dependencies={"bt_contact_router": Provide(bt_contact_router_open_access_dep)},
)
async def get_extrinsic_endpoint(
    bt_contact_router: BittensorContactRouter, block_number: BlockNumber, extrinsic_index: ExtrinsicIndex
) -> GetExtrinsicResponse:
    extrinsic = await BlockService.get_extrinsic(bt_contact_router, block_number, extrinsic_index)
    return GetExtrinsicResponse.model_validate(extrinsic, from_attributes=True)


@handler(
    Endpoint.DRAND_LAST_STORED_ROUND,
    dependencies={"bt_contact_router": Provide(bt_contact_router_open_access_dep)},
)
async def get_last_stored_round_endpoint(bt_contact_router: BittensorContactRouter) -> GetDrandLastStoredRoundResponse:
    """
    Get the last stored drand round from the blockchain.
    """
    last_stored_round = await bt_contact_router.get_drand_last_stored_round()
    return GetDrandLastStoredRoundResponse(last_stored_round=last_stored_round)


class BaseController:
    @handler(Endpoint.NEURONS)
    async def get_neurons(
        self, bt_contact_router: BittensorContactRouter, block_number: BlockNumber, netuid: NetUid
    ) -> GetNeuronsResponse:
        neurons = await NeuronService.get_neurons(bt_contact_router, netuid, block_number)
        return GetNeuronsResponse.model_validate(neurons, from_attributes=True)

    @handler(Endpoint.LATEST_NEURONS)
    async def get_latest_neurons(self, bt_contact_router: BittensorContactRouter, netuid: NetUid) -> GetNeuronsResponse:
        neurons = await NeuronService.get_latest_neurons(bt_contact_router, netuid)
        return GetNeuronsResponse.model_validate(neurons, from_attributes=True)

    @handler(Endpoint.RECENT_NEURONS)
    async def get_recent_neurons(self, recent_object_provider: RecentObjectProvider) -> GetNeuronsResponse:
        neurons = await NeuronService.get_recent_neurons(recent_object_provider)
        return GetNeuronsResponse.model_validate(neurons, from_attributes=True)

    @handler(Endpoint.VALIDATORS)
    async def get_validators(
        self, bt_contact_router: BittensorContactRouter, block_number: BlockNumber, netuid: NetUid
    ) -> GetValidatorsResponse:
        validators = await NeuronService.get_validators(bt_contact_router, netuid, block_number)
        return GetValidatorsResponse.model_validate(validators, from_attributes=True)

    @handler(Endpoint.LATEST_VALIDATORS)
    async def get_latest_validators(
        self, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> GetValidatorsResponse:
        validators = await NeuronService.get_latest_validators(bt_contact_router, netuid)
        return GetValidatorsResponse.model_validate(validators, from_attributes=True)

    @handler(Endpoint.CERTIFICATES)
    async def get_certificates_endpoint(
        self, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> dict[Hotkey, NeuronCertificate]:
        return await CertificateService.get_certificates(bt_contact_router, netuid)

    @handler(Endpoint.CERTIFICATES_HOTKEY)
    async def get_certificate_endpoint(
        self, hotkey: Hotkey, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> NeuronCertificate:
        return await CertificateService.get_certificate(bt_contact_router, netuid, hotkey)

    @handler(Endpoint.LATEST_COMMITMENTS)
    async def get_commitments_endpoint(
        self, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> GetCommitmentsResponse:
        commitments = await CommitmentService.get_commitments(bt_contact_router, netuid)
        return GetCommitmentsResponse.model_validate(commitments, from_attributes=True)

    @handler(Endpoint.LATEST_COMMITMENTS_HOTKEY)
    async def get_commitment_endpoint(
        self, hotkey: Hotkey, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> GetCommitmentResponse:
        block, commitment = await CommitmentService.get_commitment(bt_contact_router, netuid, hotkey)
        return GetCommitmentResponse(block=block, commitment=commitment)

    @handler(Endpoint.LATEST_COMMITMENTS_REVEALED)
    async def get_all_revealed_commitments_endpoint(
        self, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> GetAllRevealedCommitmentsResponse:
        commitments = await CommitmentService.get_all_revealed_commitments(bt_contact_router, netuid)
        return GetAllRevealedCommitmentsResponse.model_validate(commitments, from_attributes=True)

    @handler(Endpoint.LATEST_COMMITMENTS_REVEALED_HOTKEY)
    async def get_revealed_commitments_endpoint(
        self, hotkey: Hotkey, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> GetRevealedCommitmentsResponse:
        block, commitments = await CommitmentService.get_revealed_commitments(bt_contact_router, netuid, hotkey)
        return GetRevealedCommitmentsResponse(block=block, commitments=commitments)

    @handler(Endpoint.SUBNET_MECHANISMS_WEIGHTS)
    async def put_mechanism_weights_endpoint(
        self, data: SetWeightsBody, bt_contact_router: BittensorContactRouter, netuid: NetUid, mechanism_id: MechanismId
    ) -> Response:
        await WeightService.set_weights(bt_contact_router, netuid, mechanism_id, data.weights)
        return Response(
            {"detail": "weights update scheduled", "count": len(data.weights)}, status_code=status_codes.HTTP_200_OK
        )

    @handler(Endpoint.COMMITMENTS)
    async def set_commitment_endpoint(
        self, bt_contact_router: BittensorContactRouter, data: SetCommitmentBody, netuid: NetUid
    ) -> Response:
        await CommitmentService.set_commitment(bt_contact_router, netuid, data.commitment)
        return Response({"detail": "Commitment set successfully."}, status_code=status_codes.HTTP_201_CREATED)

    @handler(Endpoint.CERTIFICATES_SELF)
    async def get_own_certificate_endpoint(self, bt_contact_router: BittensorContactRouter, netuid: NetUid) -> Response:
        certificate = await CertificateService.get_own_certificate(bt_contact_router, netuid)
        return Response(certificate, status_code=status_codes.HTTP_200_OK)

    @handler(Endpoint.LATEST_COMMITMENTS_SELF)
    async def get_own_commitment_endpoint(
        self, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> GetCommitmentResponse:
        block, commitment = await CommitmentService.get_own_commitment(bt_contact_router, netuid)
        return GetCommitmentResponse(block=block, commitment=commitment)

    @handler(Endpoint.REVEALED_COMMITMENTS)
    async def set_revealed_commitment_endpoint(
        self, bt_contact_router: BittensorContactRouter, data: SetRevealedCommitmentBody, netuid: NetUid
    ) -> SetRevealedCommitmentResponse:
        reveal_round = await CommitmentService.set_revealed_commitment(
            bt_contact_router, netuid, data.commitment, data.blocks_until_reveal
        )
        return SetRevealedCommitmentResponse(reveal_round=reveal_round)

    @handler(Endpoint.LATEST_COMMITMENTS_REVEALED_SELF)
    async def get_own_revealed_commitments_endpoint(
        self, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> GetRevealedCommitmentsResponse:
        block, commitments = await CommitmentService.get_own_revealed_commitments(bt_contact_router, netuid)
        return GetRevealedCommitmentsResponse(block=block, commitments=commitments)

    @handler(Endpoint.CERTIFICATES_GENERATE)
    async def generate_certificate_keypair_endpoint(
        self, bt_contact_router: BittensorContactRouter, data: GenerateCertificateKeypairRequest, netuid: NetUid
    ) -> Response:
        certificate_keypair = await CertificateService.generate_certificate_keypair(
            bt_contact_router, netuid, data.algorithm
        )
        return Response(certificate_keypair, status_code=status_codes.HTTP_201_CREATED)


class OpenAccessController(Controller):
    path = "/subnet/{netuid:int}/"
    guards = [open_access_auth_guard]
    dependencies = {
        "bt_contact_router": Provide(bt_contact_router_open_access_dep),
        "recent_object_provider": Provide(recent_object_provider_open_access_dep),
    }

    get_neurons = BaseController.get_neurons
    get_latest_neurons = BaseController.get_latest_neurons
    get_recent_neurons = BaseController.get_recent_neurons
    get_validators = BaseController.get_validators
    get_latest_validators = BaseController.get_latest_validators
    get_certificates_endpoint = BaseController.get_certificates_endpoint
    get_certificate_endpoint = BaseController.get_certificate_endpoint
    get_commitments_endpoint = BaseController.get_commitments_endpoint
    get_commitment_endpoint = BaseController.get_commitment_endpoint
    get_all_revealed_commitments_endpoint = BaseController.get_all_revealed_commitments_endpoint
    get_revealed_commitments_endpoint = BaseController.get_revealed_commitments_endpoint


class IdentityController(Controller):
    path = "/identity/{identity_name:str}/subnet/{netuid:int}"
    guards = [identity_auth_guard]
    before_request = check_identity_netuid
    dependencies = {
        "identity": Provide(identity_dep),
        "bt_contact_router": Provide(bt_contact_router_identity_dep),
        "recent_object_provider": Provide(recent_object_provider_identity_dep),
    }

    get_neurons = BaseController.get_neurons
    get_latest_neurons = BaseController.get_latest_neurons
    get_recent_neurons = BaseController.get_recent_neurons
    get_validators = BaseController.get_validators
    get_latest_validators = BaseController.get_latest_validators
    get_certificates_endpoint = BaseController.get_certificates_endpoint
    get_certificate_endpoint = BaseController.get_certificate_endpoint
    get_commitments_endpoint = BaseController.get_commitments_endpoint
    get_commitment_endpoint = BaseController.get_commitment_endpoint
    get_all_revealed_commitments_endpoint = BaseController.get_all_revealed_commitments_endpoint
    get_revealed_commitments_endpoint = BaseController.get_revealed_commitments_endpoint
    put_mechanism_weights_endpoint = BaseController.put_mechanism_weights_endpoint
    set_commitment_endpoint = BaseController.set_commitment_endpoint
    get_own_certificate_endpoint = BaseController.get_own_certificate_endpoint
    get_own_commitment_endpoint = BaseController.get_own_commitment_endpoint
    set_revealed_commitment_endpoint = BaseController.set_revealed_commitment_endpoint
    get_own_revealed_commitments_endpoint = BaseController.get_own_revealed_commitments_endpoint
    generate_certificate_keypair_endpoint = BaseController.generate_certificate_keypair_endpoint


__all__ = ["BaseController", "OpenAccessController", "IdentityController", "get_identities", "get_extrinsic_endpoint"]
