# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Base configuration
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict, cast

from go_vendor_tools.config.archive import ArchiveConfig, create_archive_config

from .licenses import LicenseConfig, create_license_config

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


if TYPE_CHECKING:
    from _typeshed import StrPath

FALSY_STRINGS = ("", "0", "false")


class BaseConfig(TypedDict):
    licensing: LicenseConfig
    archive: ArchiveConfig


def create_base_config(data: dict[str, Any] | None = None) -> BaseConfig:
    data = {} if data is None else data.copy()
    data["licensing"] = create_license_config(data.get("licensing"))
    data["archive"] = create_archive_config(data.get("archive"))
    return cast(BaseConfig, data)


def load_config(
    config: StrPath | None = None, allow_missing: bool = False
) -> BaseConfig:
    """
    Load the configuration TOML file if `config` is not None
    """
    if allow_missing and config and not Path(config).is_file():
        config = None
    if not config:
        return create_base_config()
    with open(config, "rb") as fp:
        data = tomllib.load(fp)
    return create_base_config(data)
