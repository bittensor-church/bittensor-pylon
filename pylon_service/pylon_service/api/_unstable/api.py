import logging

from litestar import Controller, Response, status_codes
from litestar.di import Provide
from litestar.exceptions import NotFoundException, ServiceUnavailableException
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
from pylon_commons.models import Hotkey, NeuronCertificate, SubnetNeurons
from pylon_commons.types import BlockNumber, ExtrinsicIndex, NetUid

from pylon_service.api._unstable.tasks import ApplyWeights, SetCommitment
from pylon_service.api.utils import handler
from pylon_service.bittensor.client import AbstractBittensorClient
from pylon_service.bittensor.recent import RecentObjectMissing, RecentObjectProvider, RecentObjectStale
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


@handler(
    Endpoint.IDENTITY_LOGIN,
    dependencies={"identity": identity_dep},
    status_code=status_codes.HTTP_200_OK,
)
async def identity_login(data: LoginBody, identity: Identity) -> IdentityLoginResponse:
    # TODO: Add real authentication and session.
    return IdentityLoginResponse(netuid=identity.netuid, identity_name=identity.identity_name)


@handler(
    Endpoint.LATEST_BLOCK_INFO,
    cache=3,
    dependencies={"bt_client": Provide(bt_client_open_access_dep)},
)
async def get_latest_block_info_endpoint(bt_client: AbstractBittensorClient) -> GetLatestBlockInfoResponse:
    """
    Get latest block info - here "latest" meaning at most a couple of seconds old.
    """
    block = await bt_client.get_latest_block()
    timestamp = await bt_client.get_block_timestamp(block)
    return GetLatestBlockInfoResponse(number=block.number, hash=block.hash, timestamp=timestamp)


@handler(
    Endpoint.EXTRINSIC,
    dependencies={"bt_client": Provide(bt_client_open_access_dep)},
)
async def get_extrinsic_endpoint(
    bt_client: AbstractBittensorClient, block_number: BlockNumber, extrinsic_index: ExtrinsicIndex
) -> GetExtrinsicResponse:
    """
    Get a decoded extrinsic from a specific block.

    This is a block-level endpoint that does not require subnet context.

    Raises:
        NotFoundException: If block or extrinsic could not be found.
    """
    block = await bt_client.get_block(block_number)
    if block is None:
        raise NotFoundException(detail=f"Block {block_number} not found.")
    extrinsic = await bt_client.get_extrinsic(block, extrinsic_index)
    if extrinsic is None:
        raise NotFoundException(detail=f"Extrinsic {block_number}-{extrinsic_index} not found.")
    return GetExtrinsicResponse.model_validate(extrinsic, from_attributes=True)


class OpenAccessController(Controller):
    path = "/subnet/{netuid:int}/"
    dependencies = {
        "bt_client": Provide(bt_client_open_access_dep),
        "recent_object_provider": Provide(recent_object_provider_open_access_dep),
    }

    @handler(Endpoint.NEURONS)
    async def get_neurons(
        self, bt_client: AbstractBittensorClient, block_number: BlockNumber, netuid: NetUid
    ) -> GetNeuronsResponse:
        """
        Get a metagraph for a block.

        Raises:
            NotFoundException: If block does not exist in subtensor.
        """
        # TurboBT struggles with fetching old blocks (like block 4671121), it is so because of broken backwards
        # compatibility in bittensor, so we are not going to fix it.
        block = await bt_client.get_block(block_number)
        if block is None:
            raise NotFoundException(detail=f"Block {block_number} not found.")
        result = await bt_client.get_neurons(netuid, block=block)
        return GetNeuronsResponse.model_validate(result, from_attributes=True)

    @handler(Endpoint.LATEST_NEURONS)
    async def get_latest_neurons(self, bt_client: AbstractBittensorClient, netuid: NetUid) -> GetNeuronsResponse:
        block = await bt_client.get_latest_block()
        result = await bt_client.get_neurons(netuid, block=block)
        return GetNeuronsResponse.model_validate(result, from_attributes=True)

    @handler(Endpoint.RECENT_NEURONS)
    async def get_recent_neurons(self, recent_object_provider: RecentObjectProvider) -> GetNeuronsResponse:
        try:
            result = await recent_object_provider.get(SubnetNeurons)
            return GetNeuronsResponse.model_validate(result, from_attributes=True)
        except RecentObjectMissing as e:
            raise ServiceUnavailableException(
                "Recent neurons data is not available. Cache update may not have finished "
                "yet or subnet may not be configured for caching recent objects."
            ) from e
        except RecentObjectStale as e:
            raise ServiceUnavailableException("Recent neurons data is stale. Cache update may be failing.") from e

    @handler(Endpoint.VALIDATORS)
    async def get_validators(
        self, bt_client: AbstractBittensorClient, block_number: BlockNumber, netuid: NetUid
    ) -> GetValidatorsResponse:
        """
        Get validators (neurons with validator_permit=True) for a block, sorted by total stake descending.

        Raises:
            NotFoundException: If block does not exist in subtensor.
        """
        block = await bt_client.get_block(block_number)
        if block is None:
            raise NotFoundException(detail=f"Block {block_number} not found.")
        result = await bt_client.get_validators(netuid, block=block)
        return GetValidatorsResponse.model_validate(result, from_attributes=True)

    @handler(Endpoint.LATEST_VALIDATORS)
    async def get_latest_validators(self, bt_client: AbstractBittensorClient, netuid: NetUid) -> GetValidatorsResponse:
        """
        Get validators (neurons with validator_permit=True) at the latest block, sorted by total stake descending.
        """
        block = await bt_client.get_latest_block()
        result = await bt_client.get_validators(netuid, block=block)
        return GetValidatorsResponse.model_validate(result, from_attributes=True)

    @handler(Endpoint.CERTIFICATES)
    async def get_certificates_endpoint(
        self, bt_client: AbstractBittensorClient, netuid: NetUid
    ) -> dict[Hotkey, NeuronCertificate]:
        """
        Get all certificates for the subnet at the latest block.
        """
        block = await bt_client.get_latest_block()
        return await bt_client.get_certificates(netuid, block)

    @handler(Endpoint.CERTIFICATES_HOTKEY)
    async def get_certificate_endpoint(
        self, hotkey: Hotkey, bt_client: AbstractBittensorClient, netuid: NetUid
    ) -> NeuronCertificate:
        """
        Get a specific certificate for a hotkey.

        Raises:
            NotFoundException: If certificate could not be found in the blockchain.
        """
        block = await bt_client.get_latest_block()
        certificate = await bt_client.get_certificate(netuid, block, hotkey=hotkey)
        if certificate is None:
            raise NotFoundException(detail="Certificate not found or error fetching.")

        return certificate

    @handler(Endpoint.LATEST_COMMITMENTS)
    async def get_commitments_endpoint(
        self, bt_client: AbstractBittensorClient, netuid: NetUid
    ) -> GetCommitmentsResponse:
        """
        Get all commitments for the subnet.
        """
        block = await bt_client.get_latest_block()
        result = await bt_client.get_commitments(netuid, block)
        return GetCommitmentsResponse.model_validate(result, from_attributes=True)

    @handler(Endpoint.LATEST_COMMITMENTS_HOTKEY)
    async def get_commitment_endpoint(
        self, hotkey: Hotkey, bt_client: AbstractBittensorClient, netuid: NetUid
    ) -> GetCommitmentResponse:
        """
        Get a specific commitment for a hotkey.

        Raises:
            NotFoundException: If commitment could not be found in the blockchain.
        """
        block = await bt_client.get_latest_block()
        commitment = await bt_client.get_commitment(netuid, block, hotkey=hotkey)
        if commitment is None:
            raise NotFoundException(detail="Commitment not found.")
        return GetCommitmentResponse(block=block, **commitment.model_dump())


class IdentityController(OpenAccessController):
    path = "/identity/{identity_name:str}/subnet/{netuid:int}"
    dependencies = {
        "identity": Provide(identity_dep),
        "bt_client": Provide(bt_client_identity_dep),
        "recent_object_provider": Provide(recent_object_provider_identity_dep),
    }

    @handler(Endpoint.SUBNET_WEIGHTS)
    async def put_weights_endpoint(
        self, data: SetWeightsBody, bt_client: AbstractBittensorClient, netuid: NetUid
    ) -> Response:
        """
        Set multiple hotkeys' weights for the current epoch in a single transaction.
        """
        ApplyWeights(bt_client, data.weights, netuid).schedule()

        return Response(
            {
                "detail": "weights update scheduled",
                "count": len(data.weights),
            },
            status_code=status_codes.HTTP_200_OK,
        )

    @handler(Endpoint.COMMITMENTS)
    async def set_commitment_endpoint(
        self, bt_client: AbstractBittensorClient, data: SetCommitmentBody, netuid: NetUid
    ) -> Response:
        """
        Set a commitment (model metadata) on chain for the wallet's hotkey.

        Raises:
            BadGatewayException: When commitment could not be set after all retries.
        """
        try:
            await SetCommitment(bt_client, netuid, data.commitment)()
        except Exception as exc:
            raise BadGatewayException(detail=str(exc)) from exc
        return Response(
            {"detail": "Commitment set successfully."},
            status_code=status_codes.HTTP_201_CREATED,
        )

    @handler(Endpoint.CERTIFICATES_SELF)
    async def get_own_certificate_endpoint(self, bt_client: AbstractBittensorClient, netuid: NetUid) -> Response:
        """
        Get a certificate for the identity's wallet.

        Raises:
            NotFoundException: If certificate could not be found in the blockchain.
        """
        block = await bt_client.get_latest_block()
        certificate = await bt_client.get_certificate(netuid, block)
        if certificate is None:
            raise NotFoundException(detail="Certificate not found or error fetching.")

        return Response(certificate, status_code=status_codes.HTTP_200_OK)

    @handler(Endpoint.LATEST_COMMITMENTS_SELF)
    async def get_own_commitment_endpoint(
        self, bt_client: AbstractBittensorClient, netuid: NetUid
    ) -> GetCommitmentResponse:
        """
        Get a commitment for the identity's wallet.

        Raises:
            NotFoundException: If commitment could not be found in the blockchain.
        """
        block = await bt_client.get_latest_block()
        commitment = await bt_client.get_commitment(netuid, block)
        if commitment is None:
            raise NotFoundException(detail="Commitment not found.")
        return GetCommitmentResponse(block=block, **commitment.model_dump())

    @handler(Endpoint.CERTIFICATES_GENERATE)
    async def generate_certificate_keypair_endpoint(
        self, bt_client: AbstractBittensorClient, data: GenerateCertificateKeypairRequest, netuid: NetUid
    ) -> Response:
        """
        Generate a certificate keypair for the app's wallet.

        Raises:
            BadGatewayException: When certificate keypair could not be generated.
        """
        certificate_keypair = await bt_client.generate_certificate_keypair(netuid, data.algorithm)
        if certificate_keypair is None:
            raise BadGatewayException(detail="Could not generate certificate pair.")

        return Response(certificate_keypair, status_code=status_codes.HTTP_201_CREATED)


__all__ = [
    "OpenAccessController",
    "IdentityController",
    "identity_login",
    "get_extrinsic_endpoint",
]
