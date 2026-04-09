from pylon_commons._unstable.responses import (
    GetCommitmentResponse,
    GetCommitmentsResponse,
    GetExtrinsicResponse,
    GetLatestBlockInfoResponse,
    GetNeuronsResponse,
    GetValidatorsResponse,
)
from pylon_commons.types import BlockNumber, ExtrinsicIndex, Hotkey, NetUid

from pylon_service.bittensor.contact import BittensorPort
from pylon_service.bittensor.models import CertificateAlgorithm, NeuronCertificate, NeuronCertificateKeypair
from pylon_service.bittensor.recent import RecentObjectProvider
from pylon_service.services.blocks import BlockService as DomainBlockService
from pylon_service.services.certificates import CertificateService as DomainCertificateService
from pylon_service.services.commitments import CommitmentService as DomainCommitmentService
from pylon_service.services.neurons import NeuronService as DomainNeuronService


class BlockService:
    def __init__(self) -> None:
        self._domain = DomainBlockService()

    async def get_latest_block_info(self, router: BittensorPort) -> GetLatestBlockInfoResponse:
        block_info = await self._domain.get_latest_block_info(router)
        return GetLatestBlockInfoResponse.model_validate(block_info, from_attributes=True)

    async def get_extrinsic(
        self, router: BittensorPort, block_number: BlockNumber, extrinsic_index: ExtrinsicIndex
    ) -> GetExtrinsicResponse:
        extrinsic = await self._domain.get_extrinsic(router, block_number, extrinsic_index)
        return GetExtrinsicResponse.model_validate(extrinsic, from_attributes=True)


class NeuronService:
    def __init__(self) -> None:
        self._domain = DomainNeuronService()
        self._blocks = DomainBlockService()

    async def get_neurons(self, router: BittensorPort, netuid: NetUid, block_number: BlockNumber) -> GetNeuronsResponse:
        block = await self._blocks.get_existing_block(router, block_number)
        subnet_neurons = await self._domain.get_neurons(router, netuid, block)
        return GetNeuronsResponse.model_validate(subnet_neurons, from_attributes=True)

    async def get_latest_neurons(self, router: BittensorPort, netuid: NetUid) -> GetNeuronsResponse:
        subnet_neurons = await self._domain.get_latest_neurons(router, netuid)
        return GetNeuronsResponse.model_validate(subnet_neurons, from_attributes=True)

    async def get_recent_neurons(self, recent_object_provider: RecentObjectProvider) -> GetNeuronsResponse:
        subnet_neurons = await self._domain.get_recent_neurons(recent_object_provider)
        return GetNeuronsResponse.model_validate(subnet_neurons, from_attributes=True)

    async def get_validators(
        self, router: BittensorPort, netuid: NetUid, block_number: BlockNumber
    ) -> GetValidatorsResponse:
        block = await self._blocks.get_existing_block(router, block_number)
        subnet_validators = await self._domain.get_validators(router, netuid, block)
        return GetValidatorsResponse.model_validate(subnet_validators, from_attributes=True)

    async def get_latest_validators(self, router: BittensorPort, netuid: NetUid) -> GetValidatorsResponse:
        subnet_validators = await self._domain.get_latest_validators(router, netuid)
        return GetValidatorsResponse.model_validate(subnet_validators, from_attributes=True)


class CertificateService:
    def __init__(self) -> None:
        self._domain = DomainCertificateService()

    async def get_certificates(self, router: BittensorPort, netuid: NetUid) -> dict[Hotkey, NeuronCertificate]:
        return await self._domain.get_certificates(router, netuid)

    async def get_certificate(self, router: BittensorPort, netuid: NetUid, hotkey: Hotkey) -> NeuronCertificate:
        return await self._domain.get_certificate(router, netuid, hotkey)

    async def get_own_certificate(self, router: BittensorPort, netuid: NetUid) -> NeuronCertificate:
        return await self._domain.get_own_certificate(router, netuid)

    async def generate_certificate_keypair(
        self, router: BittensorPort, netuid: NetUid, algorithm: CertificateAlgorithm
    ) -> NeuronCertificateKeypair:
        return await self._domain.generate_certificate_keypair(router, netuid, algorithm)


class CommitmentService:
    def __init__(self) -> None:
        self._domain = DomainCommitmentService()

    async def get_commitments(self, router: BittensorPort, netuid: NetUid) -> GetCommitmentsResponse:
        block = await router.get_latest_block()
        commitments = await self._domain.get_commitments(router, netuid, block)
        return GetCommitmentsResponse.model_validate(commitments, from_attributes=True)

    async def get_commitment(self, router: BittensorPort, netuid: NetUid, hotkey: Hotkey) -> GetCommitmentResponse:
        block, commitment = await self._domain.get_commitment(router, netuid, hotkey)
        return GetCommitmentResponse(block=block, **commitment.model_dump())

    async def get_own_commitment(self, router: BittensorPort, netuid: NetUid) -> GetCommitmentResponse:
        block, commitment = await self._domain.get_own_commitment(router, netuid)
        return GetCommitmentResponse(block=block, **commitment.model_dump())
