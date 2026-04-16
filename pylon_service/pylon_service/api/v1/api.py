import re

from litestar import Controller, Request, Response, status_codes
from litestar.di import Provide
from litestar.exceptions import NotFoundException
from litestar.response import Redirect
from pylon_commons._unstable.requests import GenerateCertificateKeypairRequest
from pylon_commons.models import Hotkey, NeuronCertificate
from pylon_commons.types import BlockNumber, NetUid
from pylon_commons.v1.bodies import SetCommitmentBody, SetRevealedCommitmentBody, SetWeightsBody
from pylon_commons.v1.endpoints import Endpoint
from pylon_commons.v1.responses import (
    GetAllRevealedCommitmentsResponse,
    GetCommitmentResponse,
    GetCommitmentsResponse,
    GetIdentitiesResponse,
    GetNeuronsResponse,
    GetRevealedCommitmentsResponse,
    GetValidatorsResponse,
    SetRevealedCommitmentResponse,
)

from pylon_service.api._unstable.api import (
    get_extrinsic_endpoint,
    get_latest_block_info_endpoint,
)
from pylon_service.api._unstable.tasks import ApplyWeights, SetCommitment, SetRevealedCommitment
from pylon_service.api.utils import handler
from pylon_service.bittensor.contact_router import BittensorContactRouter
from pylon_service.bittensor.recent import RecentObjectProvider
from pylon_service.dependencies import (
    bt_contact_router_identity_dep,
    bt_contact_router_open_access_dep,
    identity_dep,
    recent_object_provider_identity_dep,
    recent_object_provider_open_access_dep,
)
from pylon_service.exceptions import BadGatewayException
from pylon_service.guards import identity_auth_guard
from pylon_service.identities import identities
from pylon_service.services.errors import CommitmentNotFoundError

from . import services

neuron_service = services.NeuronService()
certificate_service = services.CertificateService()
commitment_service = services.CommitmentService()


@handler(
    Endpoint.IDENTITIES,
    status_code=status_codes.HTTP_200_OK,
)
async def get_identities() -> GetIdentitiesResponse:
    return GetIdentitiesResponse(identities={name: identity.netuid for name, identity in identities.items()})


def identity_handler(endpoint: Endpoint, **kwargs):
    return handler(endpoint, name=f"identity_{endpoint.reverse}", **kwargs)


class OpenAccessController(Controller):
    path = "/subnet/{netuid:int}/"
    dependencies = {
        "bt_contact_router": Provide(bt_contact_router_open_access_dep),
        "recent_object_provider": Provide(recent_object_provider_open_access_dep),
    }

    @handler(Endpoint.NEURONS)
    async def get_neurons(
        self, bt_contact_router: BittensorContactRouter, block_number: BlockNumber, netuid: NetUid
    ) -> GetNeuronsResponse:
        return await neuron_service.get_neurons(bt_contact_router, netuid, block_number)

    @handler(Endpoint.LATEST_NEURONS)
    async def get_latest_neurons(self, bt_contact_router: BittensorContactRouter, netuid: NetUid) -> GetNeuronsResponse:
        return await neuron_service.get_latest_neurons(bt_contact_router, netuid)

    @handler(Endpoint.RECENT_NEURONS)
    async def get_recent_neurons(self, recent_object_provider: RecentObjectProvider) -> GetNeuronsResponse:
        return await neuron_service.get_recent_neurons(recent_object_provider)

    @handler(Endpoint.VALIDATORS)
    async def get_validators(
        self, bt_contact_router: BittensorContactRouter, block_number: BlockNumber, netuid: NetUid
    ) -> GetValidatorsResponse:
        return await neuron_service.get_validators(bt_contact_router, netuid, block_number)

    @handler(Endpoint.LATEST_VALIDATORS)
    async def get_latest_validators(
        self, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> GetValidatorsResponse:
        return await neuron_service.get_latest_validators(bt_contact_router, netuid)

    @handler(Endpoint.CERTIFICATES)
    async def get_certificates_endpoint(
        self, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> dict[Hotkey, NeuronCertificate]:
        return await certificate_service.get_certificates(bt_contact_router, netuid)

    @handler(Endpoint.CERTIFICATES_HOTKEY)
    async def get_certificate_endpoint(
        self, hotkey: Hotkey, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> NeuronCertificate:
        return await certificate_service.get_certificate(bt_contact_router, netuid, hotkey)

    @handler(Endpoint.LATEST_COMMITMENTS)
    async def get_commitments_endpoint(
        self, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> GetCommitmentsResponse:
        return await commitment_service.get_commitments(bt_contact_router, netuid)

    @handler(Endpoint.LATEST_COMMITMENTS_HOTKEY)
    async def get_commitment_endpoint(
        self, hotkey: Hotkey, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> GetCommitmentResponse:
        return await commitment_service.get_commitment(bt_contact_router, netuid, hotkey)

    @handler(Endpoint.LATEST_COMMITMENTS_REVEALED)
    async def get_all_revealed_commitments_endpoint(
        self, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> GetAllRevealedCommitmentsResponse:
        return await commitment_service.get_all_revealed_commitments(bt_contact_router, netuid)

    @handler(Endpoint.LATEST_COMMITMENTS_REVEALED_HOTKEY)
    async def get_revealed_commitments_endpoint(
        self, hotkey: Hotkey, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> GetRevealedCommitmentsResponse:
        try:
            return await commitment_service.get_revealed_commitments(bt_contact_router, netuid, hotkey)
        except CommitmentNotFoundError as exc:
            raise NotFoundException(detail="Commitments not found.") from exc


async def _check_identity_netuid(request: Request) -> Response | None:
    identity_name = request.path_params["identity_name"]
    netuid = request.path_params["netuid"]
    identity = identities.get(identity_name)
    if identity and identity.netuid != netuid:
        correct_path = re.sub(r"/subnet/\d+", f"/subnet/{identity.netuid}", request.url.path, count=1)
        return Redirect(path=correct_path, status_code=308)
    return None


class IdentityController(Controller):
    path = "/identity/{identity_name:str}/subnet/{netuid:int}"
    guards = [identity_auth_guard]
    before_request = _check_identity_netuid
    dependencies = {
        "identity": Provide(identity_dep),
        "bt_contact_router": Provide(bt_contact_router_identity_dep),
        "recent_object_provider": Provide(recent_object_provider_identity_dep),
    }

    @identity_handler(Endpoint.NEURONS)
    async def get_neurons(
        self, bt_contact_router: BittensorContactRouter, block_number: BlockNumber, netuid: NetUid
    ) -> GetNeuronsResponse:
        return await neuron_service.get_neurons(bt_contact_router, netuid, block_number)

    @identity_handler(Endpoint.LATEST_NEURONS)
    async def get_latest_neurons(self, bt_contact_router: BittensorContactRouter, netuid: NetUid) -> GetNeuronsResponse:
        return await neuron_service.get_latest_neurons(bt_contact_router, netuid)

    @identity_handler(Endpoint.RECENT_NEURONS)
    async def get_recent_neurons(self, recent_object_provider: RecentObjectProvider) -> GetNeuronsResponse:
        return await neuron_service.get_recent_neurons(recent_object_provider)

    @identity_handler(Endpoint.VALIDATORS)
    async def get_validators(
        self, bt_contact_router: BittensorContactRouter, block_number: BlockNumber, netuid: NetUid
    ) -> GetValidatorsResponse:
        return await neuron_service.get_validators(bt_contact_router, netuid, block_number)

    @identity_handler(Endpoint.LATEST_VALIDATORS)
    async def get_latest_validators(
        self, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> GetValidatorsResponse:
        return await neuron_service.get_latest_validators(bt_contact_router, netuid)

    @identity_handler(Endpoint.CERTIFICATES)
    async def get_certificates_endpoint(
        self, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> dict[Hotkey, NeuronCertificate]:
        return await certificate_service.get_certificates(bt_contact_router, netuid)

    @identity_handler(Endpoint.CERTIFICATES_HOTKEY)
    async def get_certificate_endpoint(
        self, hotkey: Hotkey, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> NeuronCertificate:
        return await certificate_service.get_certificate(bt_contact_router, netuid, hotkey)

    @identity_handler(Endpoint.CERTIFICATES_SELF)
    async def get_own_certificate_endpoint(self, bt_contact_router: BittensorContactRouter, netuid: NetUid) -> Response:
        certificate = await certificate_service.get_own_certificate(bt_contact_router, netuid)
        return Response(certificate, status_code=status_codes.HTTP_200_OK)

    @identity_handler(Endpoint.CERTIFICATES_GENERATE)
    async def generate_certificate_keypair_endpoint(
        self, bt_contact_router: BittensorContactRouter, data: GenerateCertificateKeypairRequest, netuid: NetUid
    ) -> Response:
        certificate_keypair = await certificate_service.generate_certificate_keypair(
            bt_contact_router, netuid, data.algorithm
        )
        return Response(certificate_keypair, status_code=status_codes.HTTP_201_CREATED)

    @identity_handler(Endpoint.LATEST_COMMITMENTS)
    async def get_commitments_endpoint(
        self, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> GetCommitmentsResponse:
        return await commitment_service.get_commitments(bt_contact_router, netuid)

    @identity_handler(Endpoint.LATEST_COMMITMENTS_HOTKEY)
    async def get_commitment_endpoint(
        self, hotkey: Hotkey, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> GetCommitmentResponse:
        return await commitment_service.get_commitment(bt_contact_router, netuid, hotkey)

    @identity_handler(Endpoint.LATEST_COMMITMENTS_SELF)
    async def get_own_commitment_endpoint(
        self, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> GetCommitmentResponse:
        return await commitment_service.get_own_commitment(bt_contact_router, netuid)

    @identity_handler(Endpoint.LATEST_COMMITMENTS_REVEALED_SELF)
    async def get_own_revealed_commitments_endpoint(
        self, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> GetRevealedCommitmentsResponse:
        try:
            return await commitment_service.get_revealed_commitments(bt_contact_router, netuid)
        except CommitmentNotFoundError as exc:
            raise NotFoundException(detail="Commitments not found.") from exc

    @identity_handler(Endpoint.SUBNET_WEIGHTS)
    async def put_weights_endpoint(
        self, data: SetWeightsBody, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> Response:
        ApplyWeights(bt_contact_router, data.weights, netuid).schedule()
        return Response(
            {"detail": "weights update scheduled", "count": len(data.weights)}, status_code=status_codes.HTTP_200_OK
        )

    @identity_handler(Endpoint.COMMITMENTS)
    async def set_commitment_endpoint(
        self, bt_contact_router: BittensorContactRouter, data: SetCommitmentBody, netuid: NetUid
    ) -> Response:
        try:
            await SetCommitment(bt_contact_router, netuid, data.commitment)()
        except Exception as exc:
            raise BadGatewayException(detail=str(exc)) from exc
        return Response({"detail": "Commitment set successfully."}, status_code=status_codes.HTTP_201_CREATED)

    @identity_handler(Endpoint.REVEALED_COMMITMENTS)
    async def set_revealed_commitment_endpoint(
        self, bt_contact_router: BittensorContactRouter, data: SetRevealedCommitmentBody, netuid: NetUid
    ) -> SetRevealedCommitmentResponse:
        try:
            reveal_round = await SetRevealedCommitment(
                bt_contact_router, netuid, data.commitment, data.blocks_until_reveal, data.block_time
            )()
        except Exception as exc:
            raise BadGatewayException(detail=str(exc)) from exc
        return SetRevealedCommitmentResponse(reveal_round=reveal_round)


__all__ = [
    "OpenAccessController",
    "IdentityController",
    "get_identities",
    "get_extrinsic_endpoint",
    "get_latest_block_info_endpoint",
]
