import logging

from litestar import Controller, Response, status_codes
from litestar.di import Provide
from litestar.exceptions import NotFoundException, ServiceUnavailableException
from litestar.handlers.http_handlers import decorators as http_decorators
from pylon_commons.bodies import LoginBody, SetCommitmentBody, SetWeightsBody
from pylon_commons.endpoints import Endpoint, EndpointV1, EndpointV2
from pylon_commons.models import (
    BlockInfoBag,
    Extrinsic,
    Hotkey,
    NeuronCertificate,
    SubnetCommitments,
    SubnetCommitmentsV2,
    SubnetNeurons,
    SubnetValidators,
)
from pylon_commons.requests import (
    GenerateCertificateKeypairRequest,
)
from pylon_commons.responses import GetCommitmentResponse, IdentityLoginResponse
from pylon_commons.types import BlockNumber, ExtrinsicIndex, NetUid

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
from pylon_service.tasks import ApplyWeights, SetCommitment

logger = logging.getLogger(__name__)


def handler(endpoint: Endpoint, **kwargs):
    """
    Decorator to create litestar handlers using endpoints defined in Endpoint enums.

    It is encouraged to define handlers with Endpoint enums so that Pylon service can share endpoint info
    with Pylon client.
    The decorator automatically sets the proper url, name and method for the endpoint,
    other kwargs may be set by passing them to this decorator.
    """
    method = getattr(http_decorators, endpoint.method.lower())
    return method(endpoint.url, name=endpoint.reverse, **kwargs)


@handler(
    EndpointV1.IDENTITY_LOGIN,
    dependencies={"identity": identity_dep},
    status_code=status_codes.HTTP_200_OK,
)
async def identity_login(data: LoginBody, identity: Identity) -> IdentityLoginResponse:
    # TODO: Add real authentication and session.
    return IdentityLoginResponse(netuid=identity.netuid, identity_name=identity.identity_name)


@handler(
    EndpointV1.LATEST_BLOCK_INFO,
    cache=3,
    dependencies={"bt_client": Provide(bt_client_open_access_dep)},
)
async def get_latest_block_info_endpoint(bt_client: AbstractBittensorClient) -> BlockInfoBag:
    """
    Get latest block info - here "latest" meaning at most a couple of seconds old.
    """
    block = await bt_client.get_latest_block()
    timestamp = await bt_client.get_block_timestamp(block)
    return BlockInfoBag(number=block.number, hash=block.hash, timestamp=timestamp)


@handler(
    EndpointV1.EXTRINSIC,
    dependencies={"bt_client": Provide(bt_client_open_access_dep)},
)
async def get_extrinsic_endpoint(
    bt_client: AbstractBittensorClient, block_number: BlockNumber, extrinsic_index: ExtrinsicIndex
) -> Extrinsic:
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
    return extrinsic


class OpenAccessController(Controller):
    path = "/subnet/{netuid:int}/"
    dependencies = {
        "bt_client": Provide(bt_client_open_access_dep),
        "recent_object_provider": Provide(recent_object_provider_open_access_dep),
    }

    @handler(EndpointV1.NEURONS)
    async def get_neurons(
        self, bt_client: AbstractBittensorClient, block_number: BlockNumber, netuid: NetUid
    ) -> SubnetNeurons:
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
        return await bt_client.get_neurons(netuid, block=block)

    @handler(EndpointV1.LATEST_NEURONS)
    async def get_latest_neurons(self, bt_client: AbstractBittensorClient, netuid: NetUid) -> SubnetNeurons:
        block = await bt_client.get_latest_block()
        return await bt_client.get_neurons(netuid, block=block)

    @handler(EndpointV1.RECENT_NEURONS)
    async def get_recent_neurons(self, recent_object_provider: RecentObjectProvider) -> SubnetNeurons:
        try:
            return await recent_object_provider.get(SubnetNeurons)
        except RecentObjectMissing as e:
            raise ServiceUnavailableException(
                "Recent neurons data is not available. Cache update may not have finished "
                "yet or subnet may not be configured for caching recent objects."
            ) from e
        except RecentObjectStale as e:
            raise ServiceUnavailableException("Recent neurons data is stale. Cache update may be failing.") from e

    @handler(EndpointV1.VALIDATORS)
    async def get_validators(
        self, bt_client: AbstractBittensorClient, block_number: BlockNumber, netuid: NetUid
    ) -> SubnetValidators:
        """
        Get validators (neurons with validator_permit=True) for a block, sorted by total stake descending.

        Raises:
            NotFoundException: If block does not exist in subtensor.
        """
        block = await bt_client.get_block(block_number)
        if block is None:
            raise NotFoundException(detail=f"Block {block_number} not found.")
        return await bt_client.get_validators(netuid, block=block)

    @handler(EndpointV1.LATEST_VALIDATORS)
    async def get_latest_validators(self, bt_client: AbstractBittensorClient, netuid: NetUid) -> SubnetValidators:
        """
        Get validators (neurons with validator_permit=True) at the latest block, sorted by total stake descending.
        """
        block = await bt_client.get_latest_block()
        return await bt_client.get_validators(netuid, block=block)

    @handler(EndpointV1.CERTIFICATES)
    async def get_certificates_endpoint(
        self, bt_client: AbstractBittensorClient, netuid: NetUid
    ) -> dict[Hotkey, NeuronCertificate]:
        """
        Get all certificates for the subnet at the latest block.
        """
        block = await bt_client.get_latest_block()
        return await bt_client.get_certificates(netuid, block)

    @handler(EndpointV1.CERTIFICATES_HOTKEY)
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

    @handler(EndpointV1.LATEST_COMMITMENTS)
    async def get_commitments_endpoint(self, bt_client: AbstractBittensorClient, netuid: NetUid) -> SubnetCommitments:
        """
        Get all commitments for the subnet (v1 format).
        """
        block = await bt_client.get_latest_block()
        v2_result = await bt_client.get_commitments(netuid, block)
        return SubnetCommitments(
            block=v2_result.block,
            commitments={hotkey: c.commitment for hotkey, c in v2_result.commitments.items()},
        )

    @handler(EndpointV1.LATEST_COMMITMENTS_HOTKEY)
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

    @handler(EndpointV1.SUBNET_WEIGHTS)
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

    @handler(EndpointV1.COMMITMENTS)
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

    @handler(EndpointV1.CERTIFICATES_SELF)
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

    @handler(EndpointV1.LATEST_COMMITMENTS_SELF)
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

    @handler(EndpointV1.CERTIFICATES_GENERATE)
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


class OpenAccessControllerV2(Controller):
    """
    V2 API controller for open access endpoints with breaking changes from V1.
    """

    path = "/subnet/{netuid:int}/"
    dependencies = {
        "bt_client": Provide(bt_client_open_access_dep),
    }

    @handler(EndpointV2.LATEST_COMMITMENTS)
    async def get_commitments_endpoint(self, bt_client: AbstractBittensorClient, netuid: NetUid) -> SubnetCommitmentsV2:
        """
        Get all commitments for the subnet (v2 format with commitment_block_number).
        """
        block = await bt_client.get_latest_block()
        return await bt_client.get_commitments(netuid, block)


class IdentityControllerV2(OpenAccessControllerV2):
    """
    V2 API controller for identity endpoints with breaking changes from V1.
    """

    path = "/identity/{identity_name:str}/subnet/{netuid:int}"
    dependencies = {
        "identity": Provide(identity_dep),
        "bt_client": Provide(bt_client_identity_dep),
    }
