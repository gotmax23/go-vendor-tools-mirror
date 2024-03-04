# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Configuration for the go_vendor_licenses command
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict, cast

from ..exceptions import LicenseError
from ..hashing import verify_hash


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
    exclude_globs: list[str]


def create_license_config(data: dict[str, Any] | None = None) -> LicenseConfig:
    data = {} if data is None else data.copy()
    data.setdefault("detector", None)
    data.setdefault("licenses", [])
    data.setdefault("exclude_globs", [])
    return cast("LicenseConfig", data)


def get_extra_licenses(
    licenses: list[LicenseEntry],
) -> tuple[dict[Path, str], list[Path]]:
    results: dict[Path, str] = {}
    not_matched: list[Path] = []
    seen: set[Path] = set()
    for lic in licenses:
        path = Path(lic["path"])
        if path in results:
            raise LicenseError(
                f"{path} was specified multiple times in the configuration!"
            )
        seen.add(path)
        if verify_hash(path, lic["sha256sum"]):
            results[path] = lic["expression"]
        else:
            not_matched.append(path)
    return results, not_matched
