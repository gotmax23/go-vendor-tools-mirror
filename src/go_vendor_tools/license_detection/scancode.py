# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
scancode-toolkit-based license detector backend
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict, cast

from go_vendor_tools.gomod import get_go_module_dirs
from go_vendor_tools.license_detection.search import find_license_files

try:
    import scancode.api  # type: ignore[import]
except ImportError:
    HAS_SCANCODE = False
else:
    HAS_SCANCODE = True

from go_vendor_tools.config.licenses import LicenseConfig
from go_vendor_tools.license_detection.base import (
    LicenseData,
    LicenseDetector,
    LicenseDetectorNotAvailableError,
    get_manual_license_entries,
    python3dist,
    reuse_path_to_license_map,
)
from go_vendor_tools.licensing import combine_licenses

if TYPE_CHECKING:
    from _typeshed import StrPath

# Based on go2rpm
# TODO(gotmax23): Change this to a verbose regex with explanatory comments like
# LICENSE_EXCLUDE_PATTERN
LICENSE_PATTERN = re.compile(
    r"(COPYING|COPYING[\.\-].*|COPYRIGHT|COPYRIGHT[\.\-].*|"
    r"COPYLEFT.*|EULA|EULA[\.\-].*|LICEN[CS]E|Li[cs]ense|li[cs]ense.md|"
    r"LICEN[CS]E[\.\-].*|.*[\.\-]LICEN[CS]E.*|"
    r"UNLICEN[CS]E|UNLICEN[CS]E[\.\-].*|"
    r"agpl[\.\-].*|gpl[\.\-].*|lgpl[\.\-].*|AGPL-.*[0-9].*|"
    r"APACHE-.*[0-9].*|BSD-.*[0-9].*|CC-BY-.*|GFDL-.*[0-9].*|"
    r"GNU-.*[0-9].*|GPL-.*[0-9].*|LGPL-.*[0-9].*|MIT.*|"
    r"MPL-.*[0-9].*|OFL-.*[0-9].*)"
)
LICENSE_EXCLUDE_PATTERN = re.compile(
    r"""
    (
        LICENSE.docs|   # Docs are not used for the build process.
        (?!)            # Dummy regex to allow a trailing "|"
    )""",
    flags=re.VERBOSE,
)


class ScancodeLicenseDict(TypedDict):
    """
    License data returned by the scancode library
    """

    detected_license_expression: str
    detected_license_expression_spdx: str
    license_detections: list[dict[str, Any]]
    license_clues: list[Any]
    percentage_of_license_text: float


def get_scancode_license_data(
    directory: Path,
    files: Iterable[Path],
) -> tuple[list[ScancodeLicenseDict], dict[Path, str]]:
    data_dicts: list[ScancodeLicenseDict] = []
    simplified_map: dict[Path, str] = {}
    for file in files:
        data = cast(
            ScancodeLicenseDict, scancode.api.get_licenses(str(directory / file))
        )
        data_dicts.append(data)
        simplified_map[file] = data["detected_license_expression_spdx"]
    return data_dicts, simplified_map


@dataclass()
class ScancodeLicenseData(LicenseData):
    """
    scancode-toolkit-specific LicenseData implementation
    """

    scancode_license_data: list[ScancodeLicenseDict]
    _combine_licenses = staticmethod(partial(combine_licenses, recursive_simplify=True))


class ScancodeLicenseDetector(LicenseDetector[ScancodeLicenseData]):
    NAME = "scancode"
    PACKAGES_NEEDED = (python3dist("scancode-toolkit"),)

    def __init__(
        self,
        cli_config: dict[str, str],
        license_config: LicenseConfig,
        find_only: bool = False,
    ) -> None:
        self._find_only = find_only
        if not self.find_only and not HAS_SCANCODE:
            raise LicenseDetectorNotAvailableError(
                "The scancode-toolkit library must be installed!"
            )
        self.cli_config = cli_config
        self.license_config = license_config

    def detect(self, directory: StrPath):
        if self.find_only:
            raise ValueError(
                "This cannot be called when class was initalized with find_only=True"
            )
        directory = Path(directory)
        reuse_roots = get_go_module_dirs(Path(directory), relative_paths=True)
        license_file_lists = find_license_files(
            directory,
            relative_paths=True,
            exclude_directories=self.license_config["exclude_directories"],
            exclude_files=self.license_config["exclude_files"],
            reuse_roots=reuse_roots,
        )
        data, license_map = get_scancode_license_data(
            directory, map(Path, license_file_lists["license"])
        )
        manual_license_map, manual_unmatched = get_manual_license_entries(
            self.license_config["licenses"], directory
        )
        license_map |= manual_license_map
        license_map |= reuse_path_to_license_map(license_file_lists["reuse"])
        return ScancodeLicenseData(
            directory=directory,
            license_map=license_map,
            undetected_licenses=set(),
            unmatched_extra_licenses=manual_unmatched,
            scancode_license_data=data,
            # FIXME(gotmax): Change the design of LicenseData to not require full paths
            extra_license_files=[
                Path(directory, file) for file in license_file_lists["notice"]
            ],
        )
