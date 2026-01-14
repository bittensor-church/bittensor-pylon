from __future__ import annotations

import ast
from pathlib import Path

import nox

PYTHON_VERSION = "3.12"
nox.options.default_venv_backend = "uv"
nox.options.stop_on_first_error = True
nox.options.reuse_existing_virtualenvs = True


@nox.session(name="test", python=PYTHON_VERSION)
def test(session):
    session.run("uv", "sync", "--active", "--extra", "dev")
    session.run("pytest", "-s", "-vv", "tests/", *session.posargs)


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


def _get_version(session: nox.Session, file_path: Path) -> str:
    content = session.run("git", "show", f"origin/master:{file_path}", external=True, silent=True)
    if not isinstance(content, str):
        raise ValueError(f"Could not read {file_path} from origin/master")
    for line in content.splitlines():
        if line.startswith("__version__"):
            return ast.literal_eval(line.split("=", 1)[1].strip())
    raise ValueError(f"Could not find __version__ in {file_path}")


@nox.session(name="release", python=False, default=False)
def release(session):
    session.run("git", "fetch", "origin", external=True)
    version = _get_version(session, Path("pylon_client/pylon_client/__init__.py"))
    tag_name = f"client-v{version}"
    tag_message = f"Pylon client {version} release"
    session.log(f"Tag: {tag_name}")
    session.log(f"Message: {tag_message}")
    answer = input("Create and push this tag? [y/N] ")
    if answer.lower() != "y":
        session.error("Aborted by user")
    session.run("git", "tag", "-a", tag_name, "-m", tag_message, "origin/master", external=True)
    session.run("git", "push", "origin", tag_name, external=True)
