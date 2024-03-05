# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Configuration for the go_vendor_archive command
"""

from __future__ import annotations

import os
from typing import Any, TypedDict, cast

DEFAULT_USE_TOP_LEVEL_DIR = False
DEFAULT_USE_MODULE_PROXY = (
    bool(os.environ.get("GO_VENDOR_ARCHIVE_USE_MODULE_PROXY")) or False
)
DEFAULT_TIDY = False


class ArchiveConfig(TypedDict):
    use_module_proxy: bool
    use_top_level_dir: bool
    # Commands to run before downloading modules
    pre_commands: list[list[str]]
    # Commands to run after downloading modules
    post_commands: list[list[str]]
    tidy: bool


def create_archive_config(config: dict[str, Any] | None = None) -> ArchiveConfig:
    config = {} if config is None else config.copy()
    config.setdefault("post_commands", [])
    config.setdefault("pre_commands", [])
    config.setdefault("tidy", DEFAULT_TIDY)
    config.setdefault("use_module_proxy", DEFAULT_USE_MODULE_PROXY)
    config.setdefault("use_top_level_dir", DEFAULT_USE_TOP_LEVEL_DIR)
    return cast(ArchiveConfig, config)
