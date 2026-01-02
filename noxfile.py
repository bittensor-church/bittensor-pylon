from __future__ import annotations

import ast
from pathlib import Path

import nox

PYTHON_VERSION = "3.12"
ROOT = Path(".")
nox.options.default_venv_backend = "uv"
nox.options.stop_on_first_error = True
nox.options.reuse_existing_virtualenvs = True


@nox.session(name="test", python=PYTHON_VERSION)
def test(session):
    """Run pytest with optional arguments forwarded from the command line."""
    session.run("uv", "sync", "--active", "--extra", "dev", "--extra", "service")
    session.run("pytest", "-s", "-vv", ".", *session.posargs, env={"PYLON_ENV_FILE": "tests/.test-env"})


@nox.session(name="format", python=PYTHON_VERSION)
def format(session):
    """Lint the code and apply fixes in-place whenever possible."""
    session.run("uv", "sync", "--active", "--extra", "format", "--extra", "dev", "--extra", "service")
    session.run("ruff", "format", ".")
    session.run("ruff", "check", "--fix", ".")
    session.run("pyright")
    # session.run("uvx", "ty", "check")


@nox.session(name="lint", python=PYTHON_VERSION)
def lint(session):
    """Check code formatting and typing without making any changes."""
    session.run("uv", "sync", "--active", "--extra", "format", "--extra", "dev", "--extra", "service")
    session.run("ruff", "format", "--check", "--diff", ".")
    session.run("ruff", "check", ".")
    session.run("pyright")


def _get_version(session: nox.Session, file_path: Path) -> str:
    content = session.run("git", "show", f"origin/master:{file_path}", external=True, silent=True)
    if not isinstance(content, str):
        raise ValueError(f"Could not read {file_path} from origin/master")
    for line in content.splitlines():
        if line.startswith("__version__"):
            return ast.literal_eval(line.split("=", 1)[1].strip())
    raise ValueError(f"Could not find __version__ in {file_path}")


def _create_and_push_tag(session: nox.Session, product: str, version_file: Path) -> None:
    session.run("git", "fetch", "origin", external=True)
    version = _get_version(session, version_file)
    tag_name = f"{product}-v{version}"
    tag_message = f"Pylon {product} {version} release"
    session.log(f"Tag: {tag_name}")
    session.log(f"Message: {tag_message}")
    answer = input("Create and push this tag? [y/N] ")
    if answer.lower() != "y":
        session.error("Aborted by user")
    session.run("git", "tag", "-a", tag_name, "-m", tag_message, "origin/master", external=True)
    session.run("git", "push", "origin", tag_name, external=True)


@nox.session(name="release-client", python=False, default=False)
def release_client(session):
    """Create and push an annotated git tag for the client release."""
    _create_and_push_tag(session, "client", ROOT / "pylon_client" / "__init__.py")


@nox.session(name="release-service", python=False, default=False)
def release_service(session):
    """Create and push an annotated git tag for the service release."""
    _create_and_push_tag(session, "service", ROOT / "pylon_client" / "service" / "__init__.py")
