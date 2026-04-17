from __future__ import annotations

import nox

PYTHON_VERSION = "3.13"
nox.options.default_venv_backend = "uv"
nox.options.stop_on_first_error = True
nox.options.reuse_existing_virtualenvs = True


@nox.session(name="test", python=PYTHON_VERSION)
def test(session):
    session.run("uv", "sync", "--active", "--extra", "dev")
    session.run("pytest", "-s", "-vv", "tests/unit/", *session.posargs, env={"PYLON_ENV_FILE": "tests/.test-env"})


@nox.session(name="test-unit-public-coverage", python=PYTHON_VERSION)
def test_unit_public_coverage(session):
    session.run("uv", "sync", "--active", "--extra", "dev")
    session.run(
        "pytest",
        "-s",
        "-vv",
        "tests/unit/",
        "--cov=pylon_service/api/_unstable",
        "--cov=pylon_service/api/v1",
        "--cov=pylon_service/services",
        "--cov-report=term-missing",
        *session.posargs,
        env={"PYLON_ENV_FILE": "tests/.test-env"},
    )


@nox.session(name="test-pact", python=PYTHON_VERSION)
def test_pact(session):
    session.run("uv", "sync", "--active", "--extra", "dev")
    session.run("pytest", "-s", "-vv", "tests/pact/", *session.posargs, env={"PYLON_ENV_FILE": "tests/.test-env"})


@nox.session(name="test-integration-contact", python=PYTHON_VERSION)
def test_integration_contact(session):
    test_integration(session, suite_sufix="contact/")


@nox.session(name="test-integration-contact-resilience", python=PYTHON_VERSION)
def test_integration_contact_resilience(session):
    test_integration(session, suite_sufix="contact_resilience/")


@nox.session(name="test-integration-e2e", python=PYTHON_VERSION)
def test_integration_e2e(session):
    test_integration(session, suite_sufix="client_service_e2e/")


@nox.session(name="test-integration", python=PYTHON_VERSION)
def test_integration(session, suite_sufix: str = ""):
    session.run("uv", "sync", "--active", "--extra", "dev")
    session.run(
        "pytest",
        "-s",
        "-vv",
        "--log-cli-level=INFO",
        f"tests/integration/{suite_sufix}",
        *session.posargs,
        env={"PYLON_ENV_FILE": "tests/.test-env"},
        interrupt_timeout=10,
        terminate_timeout=2,
    )


@nox.session(name="format", python=PYTHON_VERSION)
def format(session):
    session.run("uv", "sync", "--active", "--extra", "dev")
    session.run("ruff", "format", ".")
    session.run("ruff", "check", "--fix", ".")
    session.run("pyright")


@nox.session(name="lint", python=PYTHON_VERSION)
def lint(session):
    session.run("uv", "sync", "--active", "--extra", "dev")
    session.run("ruff", "format", "--check", "--diff", ".")
    session.run("ruff", "check", ".")
    session.run("pyright")


@nox.session(name="release", python=False, default=False)
def release(session):
    if session.posargs:
        version = session.posargs[0]
    else:
        version = input("Enter version to release: ")
        if not version:
            session.error("Version required")
    tag_name = f"service-v{version}"
    tag_message = f"Pylon service {version} release"
    session.run("git", "fetch", "origin", external=True)
    session.log(f"Tag: {tag_name}")
    session.log(f"Message: {tag_message}")
    answer = input("Create and push this tag? [y/N] ")
    if answer.lower() != "y":
        session.error("Aborted by user")
    session.run("git", "tag", "-a", tag_name, "-m", tag_message, "origin/master", external=True)
    session.run("git", "push", "origin", tag_name, external=True)


@nox.session(name="prepare-e2e-localchain", python=PYTHON_VERSION, default=False)
def prepare_e2e_localchain(session):
    """
    Prepare the local subtensor chain snapshot for integration tests.

    Creates a Docker image with pre-configured chain state (subnets, neurons, stake).
    Run this once to create the snapshot, or when the chain state needs updating.

    Usage:
      nox -s prepare-localchain
    """
    session.run("uv", "sync", "--active", "--extra", "dev")
    session.run(
        "uv",
        "run",
        "--active",
        "python",
        "-m",
        "tests.integration.localchain.prepare_e2e_chain",
        interrupt_timeout=10,
        terminate_timeout=2,
    )


@nox.session(name="prepare-contact-localchain", python=PYTHON_VERSION, default=False)
def prepare_contact_localchain(session):
    """
    Prepare the local subtensor chain snapshot for contact integration tests.

    Creates a Docker image with pre-configured chain state (subnets, neurons, stake).
    Run this once to create the snapshot, or when the chain state needs updating.

    Usage:
      nox -s prepare-contact-localchain
    """
    session.run("uv", "sync", "--active", "--extra", "dev")
    session.run(
        "uv",
        "run",
        "--active",
        "python",
        "-m",
        "tests.integration.localchain.prepare_contact_chain",
    )


@nox.session(name="build-docker", python=False, default=False)
def build_docker(session):
    session.run(
        "docker",
        "build",
        "-f",
        "Dockerfile",
        *session.posargs,
        "..",
        external=True,
    )
