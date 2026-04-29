"""Custom commitizen plugins filtering changelog entries by the `Impacts:` footer."""

from __future__ import annotations

from commitizen.cz.conventional_commits import ConventionalCommitsCz

_CLIENT_CHANGELOG_PATTERN = r"(?ims).*^impacts:\s*[^\n]*\b(client|commons)\b.*"
_SERVICE_CHANGELOG_PATTERN = r"(?ims).*^impacts:\s*[^\n]*\b(service|commons)\b.*"


class PylonClientCz(ConventionalCommitsCz):
    """Conventional Commits plugin for the pylon_client changelog."""

    changelog_pattern = _CLIENT_CHANGELOG_PATTERN


class PylonServiceCz(ConventionalCommitsCz):
    """Conventional Commits plugin for the pylon_service changelog."""

    changelog_pattern = _SERVICE_CHANGELOG_PATTERN
