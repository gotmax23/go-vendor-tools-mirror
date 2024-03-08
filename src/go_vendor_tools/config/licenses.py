# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Configuration for the go_vendor_licenses command
"""

from __future__ import annotations

import os
from typing import Any, TypedDict, cast


class LicenseEntry(TypedDict, total=False):
    path: str
    sha256sum: str
    expression: str


class LicenseConfig(TypedDict, total=False):
    """
    TypedDict representing the script's config file
    """

    detector: str | None
    licenses: list[LicenseEntry]
    exclude_directories: list[str]
    exclude_files: list[str]


def create_license_config(data: dict[str, Any] | None = None) -> LicenseConfig:
    data = {} if data is None else data.copy()
    data.setdefault("detector", os.environ.get("GO_VENDOR_LICENSE_DETECTOR"))
    data.setdefault("licenses", [])
    data.setdefault("exclude_globs", [])
    data.setdefault("exclude_directories", [])
    data.setdefault("exclude_files", [])
    return cast("LicenseConfig", data)
