# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Parse go.mod and modules.txt files
"""

from __future__ import annotations

import re
from collections.abc import Collection
from pathlib import Path

MODULE_REGEX = re.compile(r"^# (?:.+=>)?(?P<ipath>\S+) v(?P<version>\S+)$")


def get_go_module_names(directory: Path, allow_missing: bool = True) -> dict[str, str]:
    results: dict[str, str] = {}
    try:
        fp = (directory / "vendor/modules.txt").open("r", encoding="utf-8")
    except FileNotFoundError:
        if not allow_missing:
            raise
        return results
    with fp:
        for line in fp:
            if match := MODULE_REGEX.match(line):
                results[match["ipath"]] = match["version"]
    return results


def get_go_module_dirs(directory: Path, relative_paths: bool = False) -> list[Path]:
    results: list[Path] = []
    for ipath in get_go_module_names(directory):
        moddir = directory / "vendor" / ipath
        if moddir.is_dir():
            results.append(
                moddir.relative_to(directory) if relative_paths else moddir.resolve()
            )
    return results


def get_unlicensed_mods(directory: Path, license_paths: Collection[Path]) -> set[Path]:
    resolved_dir = directory.resolve()
    licensed_dirs = {
        (
            first.parent
            if (first := path.parent).relative_to(resolved_dir).name == "LICENSES"
            else first
        )
        for path in (p.resolve() for p in license_paths)
    }
    all_dirs = {*get_go_module_dirs(directory), directory.resolve()}
    return all_dirs - licensed_dirs
