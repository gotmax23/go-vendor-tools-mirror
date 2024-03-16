# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Configuration for the go_vendor_archive command
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Mapping, TypedDict, cast

from .utils import get_envvar_boolean

DEFAULT_USE_TOP_LEVEL_DIR = False
DEFAULT_USE_MODULE_PROXY = get_envvar_boolean(
    "GO_VENDOR_ARCHIVE_USE_MODULE_PROXY", True
)
DEFAULT_TIDY = True


class ArchiveConfig(TypedDict):
    use_module_proxy: bool
    use_top_level_dir: bool
    # Commands to run before downloading modules
    pre_commands: list[list[str]]
    # Commands to run after downloading modules
    post_commands: list[list[str]]
    tidy: bool
    dependency_overrides: dict[str, str]


def create_archive_config(config: dict[str, Any] | None = None) -> ArchiveConfig:
    # Keep the same order here as in ArchiveConfig definition
    config = {} if config is None else config.copy()
    config.setdefault("use_module_proxy", DEFAULT_USE_MODULE_PROXY)
    config.setdefault("use_top_level_dir", DEFAULT_USE_TOP_LEVEL_DIR)
    config.setdefault("pre_commands", [])
    config.setdefault("post_commands", [])
    config.setdefault("tidy", DEFAULT_TIDY)
    config.setdefault("dependency_overrides", {})
    return cast(ArchiveConfig, config)


def get_go_dependency_update_commands(
    dependency_overrides: Mapping[str, str]
) -> Iterator[tuple[str, ...]]:
    for ipath, version in dependency_overrides.items():
        yield ("go", "get", f"{ipath}@{version}")
