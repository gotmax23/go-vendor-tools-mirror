# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Configuration for the go_vendor_archive command
"""

from __future__ import annotations

from typing import Any, TypedDict, cast

DEFAULT_USE_TOP_LEVEL_DIR = False
DEFAULT_USE_MODULE_PROXY = False


class ArchiveConfig(TypedDict):
    use_module_proxy: bool
    use_top_level_dir: bool
    # Commands to run before downloading modules
    pre_commands: list[list[str]]
    # Commands to run after downloading modules
    post_commands: list[list[str]]


def create_archive_config(config: dict[str, Any] | None = None) -> ArchiveConfig:
    config = {} if config is None else config.copy()
    config.setdefault("use_top_level_dir", DEFAULT_USE_TOP_LEVEL_DIR)
    config.setdefault("use_module_proxy", DEFAULT_USE_MODULE_PROXY)
    config.setdefault("pre_commands", [])
    config.setdefault("post_commands", [])
    return cast(ArchiveConfig, config)
