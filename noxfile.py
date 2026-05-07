from __future__ import annotations

import subprocess
from pathlib import Path

import nox

PACKAGES = ["pylon_commons", "pylon_client", "pylon_service"]

nox.options.stop_on_first_error = True


def _run_nox_in_package(session: nox.Session, package: str, nox_session: str) -> None:
    session.log(f"Running '{nox_session}' in {package}")
    result = subprocess.run(
        ["nox", "-s", nox_session, "--", *session.posargs],
        cwd=Path(package),
        check=False,
    )
    if result.returncode != 0:
        session.error(f"Session '{nox_session}' failed in {package}")


@nox.session(name="test", python=False)
def test(session):
    for package in PACKAGES:
        _run_nox_in_package(session, package, "test")


@nox.session(name="test-pact", python=False)
def test_pact(session):
    _run_nox_in_package(session, "pylon_client", "test-pact")
    _run_nox_in_package(session, "pylon_service", "test-pact")


@nox.session(name="test-integration", python=False)
def test_integration(session):
    _run_nox_in_package(session, "pylon_service", "test-integration")


@nox.session(name="prepare-localchain", python=False, default=False)
def prepare_localchain(session):
    _run_nox_in_package(session, "pylon_service", "prepare-e2e-localchain")
    _run_nox_in_package(session, "pylon_service", "prepare-contact-localchain")


@nox.session(name="format", python=False)
def format(session):
    for package in PACKAGES:
        _run_nox_in_package(session, package, "format")


@nox.session(name="lint", python=False)
def lint(session):
    for package in PACKAGES:
        _run_nox_in_package(session, package, "lint")


@nox.session(name="build-docker", python=False, default=False)
def build_docker(session):
    session.run(
        "docker", "build", "-f", "pylon_service/Dockerfile", *session.posargs, ".",
        external=True,
    )
