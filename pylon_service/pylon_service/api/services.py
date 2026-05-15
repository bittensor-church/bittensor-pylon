from pylon_service.bittensor.contact import BittensorPort


class BaseService:
    def __init__(self, contact_router: BittensorPort) -> None:
        self.contact_router = contact_router


class ServiceError(Exception):
    pass


class BlockNotFoundError(ServiceError):
    pass


class ExtrinsicNotFoundError(ServiceError):
    pass


class RecentObjectMissingError(ServiceError):
    pass


class RecentObjectStaleError(ServiceError):
    pass


class CertificateNotFoundError(ServiceError):
    pass


class CertificateGenerationFailedError(ServiceError):
    pass


class CommitmentNotFoundError(ServiceError):
    pass


class CommitmentSubmissionFailedError(ServiceError):
    pass


class HyperparamsNotFoundError(ServiceError):
    pass
