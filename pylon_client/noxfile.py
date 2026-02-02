from __future__ import annotations

import nox

PYTHON_VERSIONS = ["3.11", "3.12", "3.13", "3.14"]
LINT_PYTHON_VERSION = "3.11"
PACT_PYTHON_VERSION = "3.14"
nox.options.default_venv_backend = "uv"
nox.options.stop_on_first_error = True
nox.options.reuse_existing_virtualenvs = True


@nox.session(name="test", python=PYTHON_VERSIONS)
def test(session):
    session.run("uv", "sync", "--active", "--extra", "dev")
    session.run("pytest", "-s", "-vv", "tests/unit/", *session.posargs)


@nox.session(name="test-pact", python=PACT_PYTHON_VERSION)
def test_pact(session):
    session.run("uv", "sync", "--active", "--extra", "dev")
    session.run("pytest", "-s", "-vv", "tests/pact/", *session.posargs)


@nox.session(name="format", python=LINT_PYTHON_VERSION)
def format(session):
    session.run("uv", "sync", "--active", "--extra", "dev")
    session.run("ruff", "format", ".")
    session.run("ruff", "check", "--fix", ".")
    session.run("pyright")


@nox.session(name="lint", python=LINT_PYTHON_VERSION)
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
    tag_name = f"client-v{version}"
    tag_message = f"Pylon client {version} release"
    session.run("git", "fetch", "origin", external=True)
    session.log(f"Tag: {tag_name}")
    session.log(f"Message: {tag_message}")
    answer = input("Create and push this tag? [y/N] ")
    if answer.lower() != "y":
        session.error("Aborted by user")
    session.run("git", "tag", "-a", tag_name, "-m", tag_message, "origin/master", external=True)
    session.run("git", "push", "origin", tag_name, external=True)
