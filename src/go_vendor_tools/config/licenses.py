# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Configuration for the go_vendor_licenses command
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TypedDict, cast

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


class LicenseEntry(TypedDict, total=False):
    path: str
    sha256sum: str
    expression: str


class LicenseConfig(TypedDict, total=False):
    """
    TypedDict representing the script's config file
    """

    licenses: list[LicenseEntry]


def load_config(config: Path | None = None) -> LicenseConfig:
    """
    Load the configuration TOML file if `config` is not None
    """
    if not config:
        return {"licenses": []}
    with config.open("rb") as fp:
        data = tomllib.load(fp)
    return cast("LicenseConfig", data)
