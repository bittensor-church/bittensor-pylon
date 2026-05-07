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
