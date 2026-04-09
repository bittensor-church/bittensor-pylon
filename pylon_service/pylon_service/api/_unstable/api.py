import logging

from litestar import Controller, Response, status_codes
from litestar.di import Provide
from pylon_commons._unstable.bodies import LoginBody, SetCommitmentBody, SetWeightsBody
from pylon_commons._unstable.endpoints import Endpoint
from pylon_commons._unstable.requests import GenerateCertificateKeypairRequest
from pylon_commons._unstable.responses import (
    GetCommitmentResponse,
    GetCommitmentsResponse,
    GetExtrinsicResponse,
    GetLatestBlockInfoResponse,
    GetNeuronsResponse,
    GetValidatorsResponse,
    IdentityLoginResponse,
)
from pylon_commons.models import Hotkey, NeuronCertificate
from pylon_commons.types import BlockNumber, ExtrinsicIndex, NetUid

from pylon_service.api._unstable import services
from pylon_service.api._unstable.tasks import ApplyWeights, SetCommitment
from pylon_service.api.utils import handler
from pylon_service.bittensor.recent import RecentObjectProvider
from pylon_service.bittensor.router import BittensorRouter
from pylon_service.dependencies import (
    bt_client_identity_dep,
    bt_client_open_access_dep,
    identity_dep,
    recent_object_provider_identity_dep,
    recent_object_provider_open_access_dep,
)
from pylon_service.exceptions import BadGatewayException
from pylon_service.identities import Identity

logger = logging.getLogger(__name__)

block_service = services.BlockService()
neuron_service = services.NeuronService()
certificate_service = services.CertificateService()
commitment_service = services.CommitmentService()


def identity_handler(endpoint: Endpoint, **kwargs):
    return handler(endpoint, name=f"identity_{endpoint.reverse}", **kwargs)


@handler(
    Endpoint.IDENTITY_LOGIN,
    dependencies={"identity": identity_dep},
    status_code=status_codes.HTTP_200_OK,
)
async def identity_login(data: LoginBody, identity: Identity) -> IdentityLoginResponse:
    return IdentityLoginResponse(netuid=identity.netuid, identity_name=identity.identity_name)


@handler(
    Endpoint.LATEST_BLOCK_INFO,
    cache=3,
    dependencies={"bt_client": Provide(bt_client_open_access_dep)},
)
async def get_latest_block_info_endpoint(bt_client: BittensorRouter) -> GetLatestBlockInfoResponse:
    return await block_service.get_latest_block_info(bt_client)


@handler(
    Endpoint.EXTRINSIC,
    dependencies={"bt_client": Provide(bt_client_open_access_dep)},
)
async def get_extrinsic_endpoint(
    bt_client: BittensorRouter, block_number: BlockNumber, extrinsic_index: ExtrinsicIndex
) -> GetExtrinsicResponse:
    return await block_service.get_extrinsic(bt_client, block_number, extrinsic_index)


class OpenAccessController(Controller):
    path = "/subnet/{netuid:int}/"
    dependencies = {
        "bt_client": Provide(bt_client_open_access_dep),
        "recent_object_provider": Provide(recent_object_provider_open_access_dep),
    }

    @identity_handler(Endpoint.NEURONS)
    async def get_neurons(
        self, bt_client: BittensorRouter, block_number: BlockNumber, netuid: NetUid
    ) -> GetNeuronsResponse:
        return await neuron_service.get_neurons(bt_client, netuid, block_number)

    @identity_handler(Endpoint.LATEST_NEURONS)
    async def get_latest_neurons(self, bt_client: BittensorRouter, netuid: NetUid) -> GetNeuronsResponse:
        return await neuron_service.get_latest_neurons(bt_client, netuid)

    @identity_handler(Endpoint.RECENT_NEURONS)
    async def get_recent_neurons(self, recent_object_provider: RecentObjectProvider) -> GetNeuronsResponse:
        return await neuron_service.get_recent_neurons(recent_object_provider)

    @identity_handler(Endpoint.VALIDATORS)
    async def get_validators(
        self, bt_client: BittensorRouter, block_number: BlockNumber, netuid: NetUid
    ) -> GetValidatorsResponse:
        return await neuron_service.get_validators(bt_client, netuid, block_number)

    @identity_handler(Endpoint.LATEST_VALIDATORS)
    async def get_latest_validators(self, bt_client: BittensorRouter, netuid: NetUid) -> GetValidatorsResponse:
        return await neuron_service.get_latest_validators(bt_client, netuid)

    @identity_handler(Endpoint.CERTIFICATES)
    async def get_certificates_endpoint(
        self, bt_client: BittensorRouter, netuid: NetUid
    ) -> dict[Hotkey, NeuronCertificate]:
        return await certificate_service.get_certificates(bt_client, netuid)

    @identity_handler(Endpoint.CERTIFICATES_HOTKEY)
    async def get_certificate_endpoint(
        self, hotkey: Hotkey, bt_client: BittensorRouter, netuid: NetUid
    ) -> NeuronCertificate:
        return await certificate_service.get_certificate(bt_client, netuid, hotkey)

    @identity_handler(Endpoint.LATEST_COMMITMENTS)
    async def get_commitments_endpoint(self, bt_client: BittensorRouter, netuid: NetUid) -> GetCommitmentsResponse:
        return await commitment_service.get_commitments(bt_client, netuid)

    @identity_handler(Endpoint.LATEST_COMMITMENTS_HOTKEY)
    async def get_commitment_endpoint(
        self, hotkey: Hotkey, bt_client: BittensorRouter, netuid: NetUid
    ) -> GetCommitmentResponse:
        return await commitment_service.get_commitment(bt_client, netuid, hotkey)


class IdentityController(Controller):
    path = "/identity/{identity_name:str}/subnet/{netuid:int}"
    dependencies = {
        "identity": Provide(identity_dep),
        "bt_client": Provide(bt_client_identity_dep),
        "recent_object_provider": Provide(recent_object_provider_identity_dep),
    }

    @handler(Endpoint.NEURONS)
    async def get_neurons(
        self, bt_client: BittensorRouter, block_number: BlockNumber, netuid: NetUid
    ) -> GetNeuronsResponse:
        return await neuron_service.get_neurons(bt_client, netuid, block_number)

    @handler(Endpoint.LATEST_NEURONS)
    async def get_latest_neurons(self, bt_client: BittensorRouter, netuid: NetUid) -> GetNeuronsResponse:
        return await neuron_service.get_latest_neurons(bt_client, netuid)

    @handler(Endpoint.RECENT_NEURONS)
    async def get_recent_neurons(self, recent_object_provider: RecentObjectProvider) -> GetNeuronsResponse:
        return await neuron_service.get_recent_neurons(recent_object_provider)

    @handler(Endpoint.VALIDATORS)
    async def get_validators(
        self, bt_client: BittensorRouter, block_number: BlockNumber, netuid: NetUid
    ) -> GetValidatorsResponse:
        return await neuron_service.get_validators(bt_client, netuid, block_number)

    @handler(Endpoint.LATEST_VALIDATORS)
    async def get_latest_validators(self, bt_client: BittensorRouter, netuid: NetUid) -> GetValidatorsResponse:
        return await neuron_service.get_latest_validators(bt_client, netuid)

    @handler(Endpoint.CERTIFICATES)
    async def get_certificates_endpoint(
        self, bt_client: BittensorRouter, netuid: NetUid
    ) -> dict[Hotkey, NeuronCertificate]:
        return await certificate_service.get_certificates(bt_client, netuid)

    @handler(Endpoint.CERTIFICATES_HOTKEY)
    async def get_certificate_endpoint(
        self, hotkey: Hotkey, bt_client: BittensorRouter, netuid: NetUid
    ) -> NeuronCertificate:
        return await certificate_service.get_certificate(bt_client, netuid, hotkey)

    @handler(Endpoint.LATEST_COMMITMENTS)
    async def get_commitments_endpoint(self, bt_client: BittensorRouter, netuid: NetUid) -> GetCommitmentsResponse:
        return await commitment_service.get_commitments(bt_client, netuid)

    @handler(Endpoint.LATEST_COMMITMENTS_HOTKEY)
    async def get_commitment_endpoint(
        self, hotkey: Hotkey, bt_client: BittensorRouter, netuid: NetUid
    ) -> GetCommitmentResponse:
        return await commitment_service.get_commitment(bt_client, netuid, hotkey)

    @identity_handler(Endpoint.SUBNET_WEIGHTS)
    async def put_weights_endpoint(self, data: SetWeightsBody, bt_client: BittensorRouter, netuid: NetUid) -> Response:
        ApplyWeights(bt_client, data.weights, netuid).schedule()
        return Response(
            {"detail": "weights update scheduled", "count": len(data.weights)}, status_code=status_codes.HTTP_200_OK
        )

    @identity_handler(Endpoint.COMMITMENTS)
    async def set_commitment_endpoint(
        self, bt_client: BittensorRouter, data: SetCommitmentBody, netuid: NetUid
    ) -> Response:
        try:
            await SetCommitment(bt_client, netuid, data.commitment)()
        except Exception as exc:
            raise BadGatewayException(detail=str(exc)) from exc
        return Response({"detail": "Commitment set successfully."}, status_code=status_codes.HTTP_201_CREATED)

    @identity_handler(Endpoint.CERTIFICATES_SELF)
    async def get_own_certificate_endpoint(self, bt_client: BittensorRouter, netuid: NetUid) -> Response:
        certificate = await certificate_service.get_own_certificate(bt_client, netuid)
        return Response(certificate, status_code=status_codes.HTTP_200_OK)

    @identity_handler(Endpoint.LATEST_COMMITMENTS_SELF)
    async def get_own_commitment_endpoint(self, bt_client: BittensorRouter, netuid: NetUid) -> GetCommitmentResponse:
        return await commitment_service.get_own_commitment(bt_client, netuid)

    @identity_handler(Endpoint.CERTIFICATES_GENERATE)
    async def generate_certificate_keypair_endpoint(
        self, bt_client: BittensorRouter, data: GenerateCertificateKeypairRequest, netuid: NetUid
    ) -> Response:
        certificate_keypair = await certificate_service.generate_certificate_keypair(
            bt_client, netuid, data.algorithm
        )
        return Response(certificate_keypair, status_code=status_codes.HTTP_201_CREATED)


__all__ = ["OpenAccessController", "IdentityController", "identity_login", "get_extrinsic_endpoint"]
