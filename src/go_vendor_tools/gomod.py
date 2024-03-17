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


def get_go_module_names(directory: Path) -> dict[str, str]:
    results: dict[str, str] = {}
    with (directory / "vendor/modules.txt").open("r", encoding="utf-8") as fp:
        for line in fp:
            if match := MODULE_REGEX.match(line):
                results[match["ipath"]] = match["version"]
    return results


def get_go_module_dirs(directory: Path) -> list[Path]:
    results: list[Path] = []
    for ipath in get_go_module_names(directory):
        moddir = directory / "vendor" / ipath
        if moddir.is_dir():
            results.append(moddir.resolve())
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
