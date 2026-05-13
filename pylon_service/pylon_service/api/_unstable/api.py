import logging

from litestar import Controller, Response, status_codes
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
    DrandService,
    NeuronService,
    WeightService,
)
from pylon_service.api.utils import check_identity_netuid, handler
from pylon_service.bittensor.recent import RecentObjectProvider
from pylon_service.dependencies import (
    IDENTITY_PROVIDERS,
    OPEN_ACCESS_PROVIDERS,
    PUBLIC_PROVIDERS,
)
from pylon_service.exceptions import BadGatewayException
from pylon_service.guards import identity_auth_guard, open_access_auth_guard
from pylon_service.identities import identities

logger = logging.getLogger(__name__)


class Handlers:
    @handler(
        Endpoint.IDENTITIES,
        status_code=status_codes.HTTP_200_OK,
    )
    async def get_identities(self) -> GetIdentitiesResponse:
        return GetIdentitiesResponse(identities={name: identity.netuid for name, identity in identities.items()})

    @handler(
        Endpoint.LATEST_BLOCK_INFO,
        cache=3,
    )
    async def get_latest_block_info_endpoint(self, unstable_block_service: BlockService) -> GetLatestBlockInfoResponse:
        block_info = await unstable_block_service.get_latest_block_info()
        return GetLatestBlockInfoResponse.model_validate(block_info, from_attributes=True)

    @handler(
        Endpoint.EXTRINSIC,
    )
    async def get_extrinsic_endpoint(
        self, unstable_block_service: BlockService, block_number: BlockNumber, extrinsic_index: ExtrinsicIndex
    ) -> GetExtrinsicResponse:
        extrinsic = await unstable_block_service.get_extrinsic(block_number, extrinsic_index)
        return GetExtrinsicResponse.model_validate(extrinsic, from_attributes=True)

    @handler(
        Endpoint.DRAND_LAST_STORED_ROUND,
    )
    async def get_last_stored_round_endpoint(
        self, unstable_drand_service: DrandService
    ) -> GetDrandLastStoredRoundResponse:
        """
        Get the last stored drand round from the blockchain.
        """
        last_stored_round = await unstable_drand_service.get_drand_last_stored_round()
        return GetDrandLastStoredRoundResponse(last_stored_round=last_stored_round)

    @handler(Endpoint.NEURONS)
    async def get_neurons(
        self, unstable_neuron_service: NeuronService, block_number: BlockNumber, netuid: NetUid
    ) -> GetNeuronsResponse:
        neurons = await unstable_neuron_service.get_neurons(netuid, block_number)
        return GetNeuronsResponse.model_validate(neurons, from_attributes=True)

    @handler(Endpoint.LATEST_NEURONS)
    async def get_latest_neurons(self, unstable_neuron_service: NeuronService, netuid: NetUid) -> GetNeuronsResponse:
        neurons = await unstable_neuron_service.get_latest_neurons(netuid)
        return GetNeuronsResponse.model_validate(neurons, from_attributes=True)

    @handler(Endpoint.RECENT_NEURONS)
    async def get_recent_neurons(
        self, unstable_neuron_service: NeuronService, recent_object_provider: RecentObjectProvider
    ) -> GetNeuronsResponse:
        neurons = await unstable_neuron_service.get_recent_neurons(recent_object_provider)
        return GetNeuronsResponse.model_validate(neurons, from_attributes=True)

    @handler(Endpoint.VALIDATORS)
    async def get_validators(
        self, unstable_neuron_service: NeuronService, block_number: BlockNumber, netuid: NetUid
    ) -> GetValidatorsResponse:
        validators = await unstable_neuron_service.get_validators(netuid, block_number)
        return GetValidatorsResponse.model_validate(validators, from_attributes=True)

    @handler(Endpoint.LATEST_VALIDATORS)
    async def get_latest_validators(
        self, unstable_neuron_service: NeuronService, netuid: NetUid
    ) -> GetValidatorsResponse:
        validators = await unstable_neuron_service.get_latest_validators(netuid)
        return GetValidatorsResponse.model_validate(validators, from_attributes=True)

    @handler(Endpoint.CERTIFICATES)
    async def get_certificates_endpoint(
        self, unstable_certificate_service: CertificateService, netuid: NetUid
    ) -> dict[Hotkey, NeuronCertificate]:
        return await unstable_certificate_service.get_certificates(netuid)

    @handler(Endpoint.CERTIFICATES_HOTKEY)
    async def get_certificate_endpoint(
        self, hotkey: Hotkey, unstable_certificate_service: CertificateService, netuid: NetUid
    ) -> NeuronCertificate:
        return await unstable_certificate_service.get_certificate(netuid, hotkey)

    @handler(Endpoint.CERTIFICATES_SELF)
    async def get_own_certificate_endpoint(
        self, unstable_certificate_service: CertificateService, netuid: NetUid
    ) -> Response:
        certificate = await unstable_certificate_service.get_own_certificate(netuid)
        return Response(certificate, status_code=status_codes.HTTP_200_OK)

    @handler(Endpoint.CERTIFICATES_GENERATE)
    async def generate_certificate_keypair_endpoint(
        self, unstable_certificate_service: CertificateService, data: GenerateCertificateKeypairRequest, netuid: NetUid
    ) -> Response:
        certificate_keypair = await unstable_certificate_service.generate_certificate_keypair(netuid, data.algorithm)
        return Response(certificate_keypair, status_code=status_codes.HTTP_201_CREATED)

    @handler(Endpoint.LATEST_COMMITMENTS)
    async def get_commitments_endpoint(
        self, unstable_commitment_service: CommitmentService, netuid: NetUid
    ) -> GetCommitmentsResponse:
        commitments = await unstable_commitment_service.get_commitments(netuid)
        return GetCommitmentsResponse.model_validate(commitments, from_attributes=True)

    @handler(Endpoint.LATEST_COMMITMENTS_HOTKEY)
    async def get_commitment_endpoint(
        self, hotkey: Hotkey, unstable_commitment_service: CommitmentService, netuid: NetUid
    ) -> GetCommitmentResponse:
        block, commitment = await unstable_commitment_service.get_commitment(netuid, hotkey)
        return GetCommitmentResponse(block=block, commitment=commitment)

    @handler(Endpoint.LATEST_COMMITMENTS_REVEALED)
    async def get_all_revealed_commitments_endpoint(
        self, unstable_commitment_service: CommitmentService, netuid: NetUid
    ) -> GetAllRevealedCommitmentsResponse:
        commitments = await unstable_commitment_service.get_all_revealed_commitments(netuid)
        return GetAllRevealedCommitmentsResponse.model_validate(commitments, from_attributes=True)

    @handler(Endpoint.LATEST_COMMITMENTS_REVEALED_HOTKEY)
    async def get_revealed_commitments_endpoint(
        self, hotkey: Hotkey, unstable_commitment_service: CommitmentService, netuid: NetUid
    ) -> GetRevealedCommitmentsResponse:
        block, commitments = await unstable_commitment_service.get_revealed_commitments(netuid, hotkey)
        return GetRevealedCommitmentsResponse(block=block, commitments=commitments)

    @handler(Endpoint.COMMITMENTS)
    async def set_commitment_endpoint(
        self, unstable_commitment_service: CommitmentService, data: SetCommitmentBody, netuid: NetUid
    ) -> Response:
        try:
            await unstable_commitment_service.set_commitment(netuid, data.commitment)
        except Exception as exc:
            raise BadGatewayException(detail=str(exc)) from exc
        return Response({"detail": "Commitment set successfully."}, status_code=status_codes.HTTP_201_CREATED)

    @handler(Endpoint.LATEST_COMMITMENTS_SELF)
    async def get_own_commitment_endpoint(
        self, unstable_commitment_service: CommitmentService, netuid: NetUid
    ) -> GetCommitmentResponse:
        block, commitment = await unstable_commitment_service.get_own_commitment(netuid)
        return GetCommitmentResponse(block=block, commitment=commitment)

    @handler(Endpoint.REVEALED_COMMITMENTS)
    async def set_revealed_commitment_endpoint(
        self, unstable_commitment_service: CommitmentService, data: SetRevealedCommitmentBody, netuid: NetUid
    ) -> SetRevealedCommitmentResponse:
        try:
            reveal_round = await unstable_commitment_service.set_revealed_commitment(
                netuid, data.commitment, data.blocks_until_reveal
            )
        except Exception as exc:
            raise BadGatewayException(detail=str(exc)) from exc
        return SetRevealedCommitmentResponse(reveal_round=reveal_round)

    @handler(Endpoint.LATEST_COMMITMENTS_REVEALED_SELF)
    async def get_own_revealed_commitments_endpoint(
        self, unstable_commitment_service: CommitmentService, netuid: NetUid
    ) -> GetRevealedCommitmentsResponse:
        block, commitments = await unstable_commitment_service.get_own_revealed_commitments(netuid)
        return GetRevealedCommitmentsResponse(block=block, commitments=commitments)

    @handler(Endpoint.SUBNET_MECHANISMS_WEIGHTS)
    async def put_mechanism_weights_endpoint(
        self, data: SetWeightsBody, unstable_weight_service: WeightService, netuid: NetUid, mechanism_id: MechanismId
    ) -> Response:
        await unstable_weight_service.set_weights(netuid, mechanism_id, data.weights)
        return Response(
            {"detail": "weights update scheduled", "count": len(data.weights)}, status_code=status_codes.HTTP_200_OK
        )


class PublicController(Controller):
    dependencies = PUBLIC_PROVIDERS

    get_identities = Handlers.get_identities
    get_latest_block_info_endpoint = Handlers.get_latest_block_info_endpoint
    get_extrinsic_endpoint = Handlers.get_extrinsic_endpoint
    get_last_stored_round_endpoint = Handlers.get_last_stored_round_endpoint


class OpenAccessController(Controller):
    path = "/subnet/{netuid:int}/"
    guards = [open_access_auth_guard]
    dependencies = OPEN_ACCESS_PROVIDERS

    get_neurons = Handlers.get_neurons
    get_latest_neurons = Handlers.get_latest_neurons
    get_recent_neurons = Handlers.get_recent_neurons
    get_validators = Handlers.get_validators
    get_latest_validators = Handlers.get_latest_validators
    get_certificates_endpoint = Handlers.get_certificates_endpoint
    get_certificate_endpoint = Handlers.get_certificate_endpoint
    get_commitments_endpoint = Handlers.get_commitments_endpoint
    get_commitment_endpoint = Handlers.get_commitment_endpoint
    get_all_revealed_commitments_endpoint = Handlers.get_all_revealed_commitments_endpoint
    get_revealed_commitments_endpoint = Handlers.get_revealed_commitments_endpoint


class IdentityController(Controller):
    path = "/identity/{identity_name:str}/subnet/{netuid:int}"
    guards = [identity_auth_guard]
    before_request = check_identity_netuid
    dependencies = IDENTITY_PROVIDERS

    get_neurons = Handlers.get_neurons
    get_latest_neurons = Handlers.get_latest_neurons
    get_recent_neurons = Handlers.get_recent_neurons
    get_validators = Handlers.get_validators
    get_latest_validators = Handlers.get_latest_validators
    get_certificates_endpoint = Handlers.get_certificates_endpoint
    get_certificate_endpoint = Handlers.get_certificate_endpoint
    get_commitments_endpoint = Handlers.get_commitments_endpoint
    get_commitment_endpoint = Handlers.get_commitment_endpoint
    get_all_revealed_commitments_endpoint = Handlers.get_all_revealed_commitments_endpoint
    get_revealed_commitments_endpoint = Handlers.get_revealed_commitments_endpoint
    put_mechanism_weights_endpoint = Handlers.put_mechanism_weights_endpoint
    set_commitment_endpoint = Handlers.set_commitment_endpoint
    get_own_certificate_endpoint = Handlers.get_own_certificate_endpoint
    get_own_commitment_endpoint = Handlers.get_own_commitment_endpoint
    set_revealed_commitment_endpoint = Handlers.set_revealed_commitment_endpoint
    get_own_revealed_commitments_endpoint = Handlers.get_own_revealed_commitments_endpoint
    generate_certificate_keypair_endpoint = Handlers.generate_certificate_keypair_endpoint


__all__ = ["Handlers", "PublicController", "OpenAccessController", "IdentityController"]
