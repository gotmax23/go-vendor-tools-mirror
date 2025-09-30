# Copyright (C) 2025 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT
from __future__ import annotations

import enum
import fnmatch
import os
import re
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _typeshed import StrPath


# Adapted from the ignore Rust crate's patterns that askalono crawl uses
# https://github.com/BurntSushi/ripgrep/blob/79cbe89deb1151e703f4d91b19af9cdcc128b765/crates/ignore/src/default_types.rs#L123
_LICENSE_GLOBS: Sequence[str] = (
    # General
    "COPYING",
    "COPYING[.-]*",
    "COPYRIGHT",
    "COPYRIGHT[.-]*",
    "EULA",
    "EULA[.-]*",
    "licen[cs]e",
    "licen[cs]e.*",
    "LICEN[CS]E",
    "LICEN[CS]E[.-]*",
    "*[.-]LICEN[CS]E*",
    # "NOTICE", "NOTICE[.-]*",
    # "PATENTS", "PATENTS[.-]*",
    "UNLICEN[CS]E",
    "UNLICEN[CS]E[.-]*",
    # GPL (gpl.txt, etc.)
    "agpl[.-]*",
    "gpl[.-]*",
    "lgpl[.-]*",
    # Other license-specific (APACHE-2.0.txt, etc.)
    "AGPL-*[0-9]*",
    "APACHE-*[0-9]*",
    "BSD-*[0-9]*",
    "CC-BY-*",
    "GFDL-*[0-9]*",
    "GNU-*[0-9]*",
    "GPL-*[0-9]*",
    "LGPL-*[0-9]*",
    "MIT-*[0-9]*",
    "MPL-*[0-9]*",
    "OFL-*[0-9]*",
    # New patterns added by go-vendor-tools
    "Li[cs]ense",
    "Li[cs]ense.*",
    "*-license.txt",
    "*-bsd.txt",
)
# _LICENSE_PATTERNS =
_LICENSE_PATTERN = re.compile(
    "(" + "|".join(map(fnmatch.translate, _LICENSE_GLOBS)) + ")"
)

_LICENSE_EXCLUDE_PATTERN = re.compile(
    r"""
    (
        .*\.go|         # Some projects have license.go files that are code
        .*\.py|         # Some projects have license.py files that are code
        (?!)            # Dummy regex to allow a trailing "|"
    )""",
    flags=re.VERBOSE,
)
# License exclude patterns that should only apply to subdirectories of vendor/.
_LICENSE_EXCLUDE_PATTERN_SUBDIR = re.compile(
    r"""
    (
        LICENSE.docs|   # Docs from vendored libs are not included in the final package
        (?!)            # Dummy regex to allow a trailing "|"
    )""",
    flags=re.VERBOSE,
)

_NOTICE_PATTERN = re.compile(r"^(AUTHORS|NOTICE|PATENTS).*$")


class LicenseFileTypes(enum.Enum):
    LICENSE_FILE = enum.auto()
    NOTICE_FILE = enum.auto()


@dataclass(frozen=True)
class LicenseRegexFileType:
    _DISALLOWED_NAMES = ("reuse",)
    name: str
    regex: re.Pattern[str]
    exclude_regex: re.Pattern[str] | None = None
    exclude_subdir_regex: re.Pattern[str] | None = None

    def __post_init__(self) -> None:
        if self.name in self._DISALLOWED_NAMES:
            raise ValueError(f"Disallowed name: {self.name}")


LICENSE_FILE_TYPE = LicenseRegexFileType(
    "license",
    _LICENSE_PATTERN,
    _LICENSE_EXCLUDE_PATTERN,
    _LICENSE_EXCLUDE_PATTERN_SUBDIR,
)
NOTICE_FILE_TYPE = LicenseRegexFileType(
    "notice", _NOTICE_PATTERN, _LICENSE_EXCLUDE_PATTERN
)
DEFAULT_FILE_TYPES = (LICENSE_FILE_TYPE, NOTICE_FILE_TYPE)


def _clean_dirnames(dirnames: Collection[object]) -> set[str]:
    return {d.rstrip("/") for d in map(str, dirnames)}


def find_license_files(
    directory: StrPath,
    relative_paths: bool,
    exclude_directories: Collection[str] = (),
    exclude_files: Collection[str] = (),
    # FIXME(gotmax23): Properly integrate and test REUSE support
    reuse_roots: Collection[StrPath] = (),
    *,
    filetype_info: Sequence[LicenseRegexFileType] = DEFAULT_FILE_TYPES,
):
    """
    Find license files of different types

    Args:
        directory: Root directory to recurse through to find license files
        relative_paths: Whether to return paths relative to `directory` or full paths
        exclude_directories: Directory paths relative to `directory` to exclude
        exclude_files: File paths relative to `directory` to exclude
        reuse_roots: Directories to search for REUSE-style LICENSES directory
    """
    licenses: dict[str, list[str]] = {ft.name: [] for ft in filetype_info}
    licenses["reuse"] = []
    exclude_directories = _clean_dirnames(exclude_directories)
    reuse_roots = _clean_dirnames(reuse_roots)
    for root, dirnames, files in os.walk(directory):
        rootpath = os.path.relpath(root, directory)
        rootbasename = os.path.basename(root)
        rootdirname = os.path.dirname(rootpath)
        in_reuse_dir = rootbasename == "LICENSES" and (
            # "" if rootdirname is the root directory, which we always want
            # to consider as a reuse directory
            rootdirname == ""
            or rootdirname in reuse_roots
        )
        if in_reuse_dir:
            # If it's a REUSE directory, we don't need to recurse any further
            dirnames.clear()
        else:
            for dirname in list(dirnames):
                dirpath = os.path.relpath(os.path.join(root, dirname), directory)
                if dirpath in exclude_directories:
                    dirnames.remove(dirname)
        for file in files:
            fullpath = os.path.join(root, file)
            filepath = os.path.relpath(fullpath, directory)
            if filepath in exclude_files:
                continue
            if in_reuse_dir:
                licenses["reuse"].append(filepath if relative_paths else fullpath)
            else:
                for ft in filetype_info:
                    if ft.regex.fullmatch(file) and (
                        (not ft.exclude_regex or not ft.exclude_regex.fullmatch(file))
                        and (
                            # Inside the root directory so n/a
                            not rootpath.startswith(f"vendor{os.sep}")
                            # Regex is None so n/a
                            or not ft.exclude_subdir_regex
                            # Regex does not match, so okay to include
                            or not ft.exclude_subdir_regex.fullmatch(file)
                        )
                    ):
                        licenses[ft.name].append(
                            filepath if relative_paths else fullpath
                        )
                        break
    return licenses
