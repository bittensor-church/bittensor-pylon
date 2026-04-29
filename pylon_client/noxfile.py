from __future__ import annotations

import nox

PYTHON_VERSIONS = ["3.11", "3.12", "3.13", "3.14"]
LINT_PYTHON_VERSION = "3.11"
PACT_PYTHON_VERSION = "3.14"
nox.options.default_venv_backend = "uv"
nox.options.stop_on_first_error = True
nox.options.reuse_existing_virtualenvs = True
MASTER_BRANCH = "master"


def _release(session):
    session.run("uv", "sync", "--group", "dev")
    dirty_files = session.run("git", "status", "--porcelain", silent=True, external=True).strip()
    if dirty_files:
        session.error("Release requires a clean worktree.")

    branch = session.run("git", "branch", "--show-current", silent=True, external=True).strip()
    if branch == MASTER_BRANCH:
        session.run("git", "pull", "--ff-only", "origin", MASTER_BRANCH, external=True)
    else:
        session.log(f"WARNING: releasing from {branch or 'detached HEAD'} instead of {MASTER_BRANCH}.")

    # We need to find the increment manually via our script as commitizen does not filter out commits by scope
    # for increment determination.
    increment = session.run("uv", "run", "python", "-m", "pylon_cz_helpers", "increment", silent=True).strip()
    if increment == "NONE":
        session.error("No releasable commits found for this package.")

    session.log(f"Detected package-filtered increment: {increment}")
    dry_run_output = session.run(
        "uv",
        "run",
        "cz",
        "bump",
        "--dry-run",
        "--increment",
        increment,
        *session.posargs,
        silent=True,
    )
    print(dry_run_output)

    confirmation_prompt = "Create release commit and tag, then push them? [y/N] "
    if branch != MASTER_BRANCH:
        confirmation_prompt = (
            f"WARNING: releasing from {branch or 'detached HEAD'} instead of {MASTER_BRANCH}.\n{confirmation_prompt}"
        )
    if input(confirmation_prompt).lower() != "y":
        session.error("Aborted by user")

    session.run("uv", "run", "cz", "bump", "--increment", increment, *session.posargs)
    session.run("git", "push", "origin", "HEAD", "--follow-tags", external=True)


@nox.session(name="test", python=PYTHON_VERSIONS)
def test(session):
    session.run("uv", "sync", "--active", "--group", "dev")
    session.run("pytest", "-s", "-vv", "tests/unit/", *session.posargs)


@nox.session(name="test-pact", python=PACT_PYTHON_VERSION)
def test_pact(session):
    session.run("uv", "sync", "--active", "--group", "dev")
    session.run("pytest", "-s", "-vv", "tests/pact/", *session.posargs)


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


@nox.session(name="release", python=False, default=False)
def release(session):
    _release(session)
