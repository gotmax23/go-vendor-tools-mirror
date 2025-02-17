# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Retrieve source entries from a specfile
"""

from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

from go_vendor_tools.exceptions import MissingDependencyError, VendorToolsError

SPECTOOL_PATH = shutil.which("spectool")

SOURCE_RE = re.compile(r"^Source(?P<number>\d+): (?P<source>.+)$", flags=re.MULTILINE)


def get_basename_heuristic(name: str) -> str:
    """
    Use a similar heuristic to that of spectool to determine a Source entry's
    basename
    """
    if "#" in name:
        _, basename = name.split("#")
        name = basename.lstrip("/")
    else:
        name = Path(name).name
    return name


def get_specfile_sources(spec_path: Path) -> Iterator[tuple[int, str]]:
    """
    Iterator of specfile sources

    Args:
        spec_path: Path to specfile

    Yields: (source number, location)
    """
    if not SPECTOOL_PATH:
        raise MissingDependencyError("spectool from rpmdevtools is missing!")
    stdout = subprocess.run(
        ["spectool", "--sources", spec_path], capture_output=True, text=True, check=True
    ).stdout.strip()
    for match in SOURCE_RE.finditer(stdout):
        yield int(match["number"]), match["source"]


def get_specfile_sources_relative(spec_path: Path) -> dict[int, str]:
    """
    Returns dictionary of specfile source numbers mapped to relative path to
    file (as determined by get_basename_heuristic())

    Args:
        spec_path: Path to specfile
    """
    return {
        number: get_basename_heuristic(source)
        for number, source in get_specfile_sources(spec_path)
    }


def get_path_and_output_from_specfile(spec_path: Path) -> tuple[Path, Path]:
    """
    Assuming that Source0 is the main archive and Source1 is the vendor archive,
    return full paths to each.

    Yields: (Source0 path, Source1 path)

    Raises:
        VendorToolsError: If Source0 and/or Source1 don't exist
    """
    sources = get_specfile_sources_relative(spec_path)
    if not {0, 1} & set(sources):
        # TODO(anyone): More specific exception class
        raise VendorToolsError(f"Source0 and Source1 must be specified in {spec_path}")
    directory = spec_path.resolve().parent
    return directory / sources[0], directory / sources[1]
