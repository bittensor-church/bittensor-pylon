import importlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest
from litestar.exceptions import NotFoundException, ServiceUnavailableException

from pylon_service.exceptions import BadGatewayException
from pylon_service.services.errors import (
    BlockNotFoundError,
    CertificateGenerationFailedError,
    CertificateNotFoundError,
    CommitmentNotFoundError,
    ExtrinsicNotFoundError,
    RecentObjectMissingError,
    RecentObjectStaleError,
)


def test_domain_exception_handlers_module_exists_and_maps_expected_exceptions():
    module_spec = importlib.util.find_spec("pylon_service.api.exception_handlers")

    assert module_spec is not None

    module = importlib.import_module("pylon_service.api.exception_handlers")

    assert set(module.domain_exception_handlers) == {
        BlockNotFoundError,
        ExtrinsicNotFoundError,
        CertificateNotFoundError,
        CommitmentNotFoundError,
        RecentObjectMissingError,
        RecentObjectStaleError,
        CertificateGenerationFailedError,
    }


def test_domain_exception_handlers_module_imports_in_fresh_interpreter():
    package_root = Path(__file__).resolve().parents[2]
    env = {**os.environ, "PYLON_ENV_FILE": "tests/.test-env"}

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from pylon_service.api.exception_handlers import domain_exception_handlers; "
                "print(sorted(cls.__name__ for cls in domain_exception_handlers))"
            ),
        ],
        capture_output=True,
        check=False,
        cwd=package_root,
        env=env,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == (
        "['BlockNotFoundError', 'CertificateGenerationFailedError', 'CertificateNotFoundError', "
        "'CommitmentNotFoundError', 'ExtrinsicNotFoundError', 'RecentObjectMissingError', "
        "'RecentObjectStaleError']"
    )


@pytest.mark.parametrize(
    ("handler_name", "source_exception", "expected_exception"),
    [
        ("handle_not_found", BlockNotFoundError("block missing"), NotFoundException),
        ("handle_service_unavailable", RecentObjectMissingError("recent cache empty"), ServiceUnavailableException),
        ("handle_bad_gateway", CertificateGenerationFailedError("certificate generation failed"), BadGatewayException),
    ],
)
def test_shared_exception_handlers_raise_expected_http_exceptions(
    handler_name: str, source_exception: Exception, expected_exception: type[Exception]
):
    module = importlib.import_module("pylon_service.api.exception_handlers")
    handler = getattr(module, handler_name)

    with pytest.raises(expected_exception, match=str(source_exception)):
        handler(None, source_exception)
