# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Configuration for the go_vendor_archive command
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict, cast

from ..exceptions import ConfigError

DEFAULT_USE_MODULE_PROXY = False


class ExtraFileEntry(TypedDict):
    url: str
    dest: Path


class ArchiveConfig(TypedDict):
    use_module_proxy: bool
    extra_files: list[ExtraFileEntry]
    # Commands to run before downloading modules
    pre_commands: list[list[str]]
    # Commands to run after downloading modules
    post_commands: list[list[str]]


def create_download_file_config(config: dict[str, Any]) -> ExtraFileEntry:
    if "url" not in config:
        raise ConfigError("url must be specified in the archive.extra_files[] config!")
    if "dest" not in config:
        raise ConfigError("dest must be specified in the archive.extra_files[] config!")
    path = Path(config["dest"])
    if path.is_absolute():
        raise ConfigError("dest in archive.extra_files[] may not be absolute!")
    return ExtraFileEntry(url=config["url"], dest=path)


def create_archive_config(config: dict[str, Any] | None = None) -> ArchiveConfig:
    config = {} if config is None else config.copy()
    config.setdefault("use_module_proxy", DEFAULT_USE_MODULE_PROXY)
    config.setdefault("extra_files", [])
    config.setdefault("pre_commands", [])
    config.setdefault("post_commands", [])
    for idx, entry in enumerate(config["extra_files"]):
        config["extra_files"][idx] = create_download_file_config(entry)
    return cast(ArchiveConfig, config)
