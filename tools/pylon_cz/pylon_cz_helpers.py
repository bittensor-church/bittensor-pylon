"""Helper CLI for pylon-cz release tooling."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import cast

from commitizen import bump, factory, git
from commitizen.config.base_config import BaseConfig
from commitizen.config.factory import create_config
from commitizen.defaults import Settings
from commitizen.providers import get_provider
from commitizen.tags import TagRules
from commitizen.version_schemes import Increment

NO_INCREMENT = "NONE"


def load_config(config_path: Path = Path("pyproject.toml")) -> BaseConfig:
    """Load a Commitizen config from an explicit path."""
    return create_config(data=config_path.read_bytes(), path=config_path)


def find_filtered_increment(config: BaseConfig) -> Increment | None:
    """
    Return the Commitizen increment after applying the configured plugin changelog filter.
    This is needed because commitizen does not filter out commit by scope when determining version increment.
    """
    cz = factory.committer_factory(config)
    if not cz.changelog_pattern or not cz.bump_pattern or not cz.bump_map:
        return None

    current_version = get_provider(config).get_version()
    rules = TagRules.from_settings(cast(Settings, config.settings))
    current_tag = rules.find_tag_for(git.get_tags(), current_version)
    commits = git.get_commits(current_tag.name if current_tag else None)

    changelog_pattern = re.compile(cz.changelog_pattern)
    filtered_commits = [commit for commit in commits if changelog_pattern.match(commit.message)]
    increments_map = cz.bump_map_major_version_zero if config.settings["major_version_zero"] else cz.bump_map
    return bump.find_increment(filtered_commits, regex=cz.bump_pattern, increments_map=increments_map)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pylon Commitizen helpers.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    increment_parser = subparsers.add_parser("increment", help="Print the package-filtered Commitizen increment.")
    increment_parser.add_argument("--config", type=Path, default=Path("pyproject.toml"))

    args = parser.parse_args()
    if args.command == "increment":
        increment = find_filtered_increment(load_config(args.config))
        print(increment or NO_INCREMENT)


if __name__ == "__main__":
    main()
