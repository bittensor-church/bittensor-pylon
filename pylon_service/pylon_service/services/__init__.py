from importlib import import_module

from .errors import (
    BlockNotFoundError,
    CertificateGenerationFailedError,
    CertificateNotFoundError,
    CommitmentNotFoundError,
    CommitmentSubmissionFailedError,
    ExtrinsicNotFoundError,
    HyperparamsNotFoundError,
    RecentObjectMissingError,
    RecentObjectStaleError,
    ServiceError,
)

_SERVICE_EXPORTS = {
    "BlockService": ".blocks",
    "CertificateService": ".certificates",
    "CommitmentService": ".commitments",
    "NeuronService": ".neurons",
    "WeightsService": ".weights",
}

__all__ = [
    "BlockNotFoundError",
    "BlockService",
    "CertificateGenerationFailedError",
    "CertificateNotFoundError",
    "CertificateService",
    "CommitmentNotFoundError",
    "CommitmentService",
    "CommitmentSubmissionFailedError",
    "ExtrinsicNotFoundError",
    "HyperparamsNotFoundError",
    "NeuronService",
    "RecentObjectMissingError",
    "RecentObjectStaleError",
    "ServiceError",
    "WeightsService",
]


def __getattr__(name: str):
    module_name = _SERVICE_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(module_name, __name__)
    return getattr(module, name)


def __dir__() -> list[str]:
    return sorted(__all__)
