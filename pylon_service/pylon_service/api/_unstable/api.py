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

from pylon_service.api._unstable import services
from pylon_service.api._unstable.tasks import ApplyWeights, SetCommitment, SetRevealedCommitment
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
from pylon_service.exceptions import BadGatewayException
from pylon_service.guards import identity_auth_guard, open_access_auth_guard
from pylon_service.identities import identities

logger = logging.getLogger(__name__)

block_service = services.BlockService()
neuron_service = services.NeuronService()
certificate_service = services.CertificateService()
commitment_service = services.CommitmentService()


def identity_handler(endpoint: Endpoint, **kwargs):
    return handler(endpoint, name=f"identity_{endpoint.reverse}", **kwargs)


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
    return await block_service.get_latest_block_info(bt_contact_router)


@handler(
    Endpoint.EXTRINSIC,
    dependencies={"bt_contact_router": Provide(bt_contact_router_open_access_dep)},
)
async def get_extrinsic_endpoint(
    bt_contact_router: BittensorContactRouter, block_number: BlockNumber, extrinsic_index: ExtrinsicIndex
) -> GetExtrinsicResponse:
    return await block_service.get_extrinsic(bt_contact_router, block_number, extrinsic_index)


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


class OpenAccessController(Controller):
    path = "/subnet/{netuid:int}/"
    guards = [open_access_auth_guard]
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
        return await commitment_service.get_revealed_commitments(bt_contact_router, netuid, hotkey)


class IdentityController(Controller):
    path = "/identity/{identity_name:str}/subnet/{netuid:int}"
    guards = [identity_auth_guard]
    before_request = check_identity_netuid
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

    @identity_handler(Endpoint.SUBNET_WEIGHTS)
    async def put_weights_endpoint(
        self, data: SetWeightsBody, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> Response:
        ApplyWeights(bt_contact_router, data.weights, netuid, MechanismId(0)).schedule()
        return Response(
            {"detail": "weights update scheduled", "count": len(data.weights)}, status_code=status_codes.HTTP_200_OK
        )

    @identity_handler(Endpoint.SUBNET_MECHANISMS_WEIGHTS)
    async def put_mechanism_weights_endpoint(
        self, data: SetWeightsBody, bt_contact_router: BittensorContactRouter, netuid: NetUid, mechanism_id: MechanismId
    ) -> Response:
        ApplyWeights(bt_contact_router, data.weights, netuid, mechanism_id).schedule()
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

    @identity_handler(Endpoint.CERTIFICATES_SELF)
    async def get_own_certificate_endpoint(self, bt_contact_router: BittensorContactRouter, netuid: NetUid) -> Response:
        certificate = await certificate_service.get_own_certificate(bt_contact_router, netuid)
        return Response(certificate, status_code=status_codes.HTTP_200_OK)

    @identity_handler(Endpoint.LATEST_COMMITMENTS_SELF)
    async def get_own_commitment_endpoint(
        self, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> GetCommitmentResponse:
        return await commitment_service.get_own_commitment(bt_contact_router, netuid)

    @identity_handler(Endpoint.REVEALED_COMMITMENTS)
    async def set_revealed_commitment_endpoint(
        self, bt_contact_router: BittensorContactRouter, data: SetRevealedCommitmentBody, netuid: NetUid
    ) -> SetRevealedCommitmentResponse:
        try:
            reveal_round = await SetRevealedCommitment(
                bt_contact_router, netuid, data.commitment, data.blocks_until_reveal
            )()
        except Exception as exc:
            raise BadGatewayException(detail=str(exc)) from exc
        return SetRevealedCommitmentResponse(reveal_round=reveal_round)

    @identity_handler(Endpoint.LATEST_COMMITMENTS_REVEALED)
    async def get_all_revealed_commitments_endpoint(
        self, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> GetAllRevealedCommitmentsResponse:
        return await commitment_service.get_all_revealed_commitments(bt_contact_router, netuid)

    @identity_handler(Endpoint.LATEST_COMMITMENTS_REVEALED_HOTKEY)
    async def get_revealed_commitments_endpoint(
        self, hotkey: Hotkey, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> GetRevealedCommitmentsResponse:
        return await commitment_service.get_revealed_commitments(bt_contact_router, netuid, hotkey)

    @identity_handler(Endpoint.LATEST_COMMITMENTS_REVEALED_SELF)
    async def get_own_revealed_commitments_endpoint(
        self, bt_contact_router: BittensorContactRouter, netuid: NetUid
    ) -> GetRevealedCommitmentsResponse:
        return await commitment_service.get_own_revealed_commitments(bt_contact_router, netuid)

    @identity_handler(Endpoint.CERTIFICATES_GENERATE)
    async def generate_certificate_keypair_endpoint(
        self, bt_contact_router: BittensorContactRouter, data: GenerateCertificateKeypairRequest, netuid: NetUid
    ) -> Response:
        certificate_keypair = await certificate_service.generate_certificate_keypair(
            bt_contact_router, netuid, data.algorithm
        )
        return Response(certificate_keypair, status_code=status_codes.HTTP_201_CREATED)


__all__ = ["OpenAccessController", "IdentityController", "get_identities", "get_extrinsic_endpoint"]
