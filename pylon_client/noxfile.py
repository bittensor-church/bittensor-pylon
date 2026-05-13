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
    session.run("uv", "sync", "--active", "--group", "dev")
    pytest_args = session.posargs or ["tests/unit/"]
    session.run("pytest", "-s", "-vv", *pytest_args)


@nox.session(name="test-pact", python=PACT_PYTHON_VERSION)
def test_pact(session):
    session.run("uv", "sync", "--active", "--group", "dev")
    pytest_args = session.posargs or ["tests/pact/"]
    session.run("pytest", "-s", "-vv", *pytest_args)


@nox.session(name="format", python=LINT_PYTHON_VERSION)
def format(session):
    session.run("uv", "sync", "--active", "--group", "dev")
    session.run("ruff", "format", ".")
    session.run("ruff", "check", "--fix", ".")
    session.run("pyright")


@nox.session(name="lint", python=LINT_PYTHON_VERSION)
def lint(session):
    session.run("uv", "sync", "--active", "--group", "dev")
    session.run("ruff", "format", "--check", "--diff", ".")
    session.run("ruff", "check", ".")
    session.run("pyright")
