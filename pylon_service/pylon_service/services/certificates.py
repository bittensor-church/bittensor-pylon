from pylon_commons.types import NetUid

from pylon_service.bittensor.contact import BittensorPort
from pylon_service.bittensor.models import Block, CertificateAlgorithm, NeuronCertificate, NeuronCertificateKeypair

from .errors import CertificateGenerationFailedError, CertificateNotFoundError


class CertificateService:
    async def get_certificates(self, router: BittensorPort, netuid: NetUid) -> dict:
        block = await router.get_latest_block()
        return await router.get_certificates(netuid, block)

    async def get_certificate(self, router: BittensorPort, netuid: NetUid, hotkey) -> NeuronCertificate:
        block = await router.get_latest_block()
        certificate = await router.get_certificate(netuid, block, hotkey=hotkey)
        if certificate is None:
            raise CertificateNotFoundError("Certificate not found or error fetching.")
        return certificate

    async def get_own_certificate(self, router: BittensorPort, netuid: NetUid) -> NeuronCertificate:
        block = await router.get_latest_block()
        certificate = await router.get_certificate(netuid, block)
        if certificate is None:
            raise CertificateNotFoundError("Certificate not found or error fetching.")
        return certificate

    async def generate_certificate_keypair(
        self, router: BittensorPort, netuid: NetUid, algorithm: CertificateAlgorithm
    ) -> NeuronCertificateKeypair:
        certificate_keypair = await router.generate_certificate_keypair(netuid, algorithm)
        if certificate_keypair is None:
            raise CertificateGenerationFailedError("Could not generate certificate pair.")
        return certificate_keypair
