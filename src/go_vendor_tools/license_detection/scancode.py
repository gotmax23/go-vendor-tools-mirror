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
    find_extra_license_files,
    get_manual_license_entries,
    python3dist,
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
        cli_config: dict[str, str],  # noqa: ARG002
        license_config: LicenseConfig,
    ) -> None:
        if not HAS_SCANCODE:
            raise LicenseDetectorNotAvailableError(
                "The scancode-toolkit library must be installed!"
            )
        self.license_config = license_config

    def detect(self, directory: StrPath):
        directory = Path(directory)
        files_it = find_extra_license_files(
            directory,
            exclude_directories=self.license_config["exclude_directories"],
            exclude_files=self.license_config["exclude_files"],
            regex=LICENSE_PATTERN,
            exclude_regex=LICENSE_EXCLUDE_PATTERN,
            relative_paths=True,
        )
        data, license_map = get_scancode_license_data(directory, files_it)
        del files_it  # Iterator has been exhausted; don't accidentially reuse
        manual_license_map, manual_unmatched = get_manual_license_entries(
            self.license_config["licenses"], directory
        )
        license_map |= manual_license_map
        extra = list(
            find_extra_license_files(
                directory,
                exclude_directories=self.license_config["exclude_directories"],
                exclude_files=self.license_config["exclude_files"],
            )
        )
        return ScancodeLicenseData(
            directory=directory,
            license_map=license_map,
            undetected_licenses=[],
            unmatched_extra_licenses=manual_unmatched,
            extra_license_files=extra,
            scancode_license_data=data,
        )
