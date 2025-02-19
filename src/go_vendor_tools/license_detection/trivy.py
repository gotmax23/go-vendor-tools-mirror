# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Detect licenses using trivy
"""

from __future__ import annotations

import dataclasses
import json
import shutil
import subprocess
from collections.abc import Sequence
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, TypedDict, cast

from go_vendor_tools.config.licenses import LicenseConfig
from go_vendor_tools.gomod import get_go_module_dirs
from go_vendor_tools.license_detection.base import reuse_path_to_license_map
from go_vendor_tools.license_detection.search import (
    NOTICE_FILE_TYPE,
    find_license_files,
)
from go_vendor_tools.licensing import combine_licenses, validate_license

from .base import (
    LicenseData,
    LicenseDetector,
    LicenseDetectorNotAvailableError,
    filter_license_map,
    get_manual_license_entries,
)

if TYPE_CHECKING:
    from _typeshed import StrPath


class TrivyLicenseFileEntry(TypedDict):
    Severity: str
    Category: str
    PkgName: str
    FilePath: str
    Name: str
    Confidence: float
    Link: str


class TrivyLicenseDict(TypedDict):
    Target: Literal["Loose File License(s)"]
    Class: Literal["license-file"]
    Licenses: list[TrivyLicenseFileEntry]


def run_read_json(command: Sequence[StrPath]) -> Any:
    proc: subprocess.CompletedProcess[str] = subprocess.run(
        command, check=True, text=True, capture_output=True
    )
    return json.loads(proc.stdout)


@dataclasses.dataclass()
class TrivyLicenseData(LicenseData):
    trivy_license_data: TrivyLicenseDict


def _load_license_data(trivy_path: StrPath, directory: StrPath) -> dict[str, Any]:
    # fmt: off
    cmd = [
        trivy_path,
        "fs",
        "--scanners", "license",
        "--license-full",
        "-f", "json",
        directory,
    ]
    # fmt: on
    return run_read_json(cmd)


def _license_data_to_trivy_license_dict(data: dict[str, Any]) -> TrivyLicenseDict:
    for item in data["Results"]:
        if item.get("Class") == "license-file":
            return cast(TrivyLicenseDict, item)
    raise ValueError("Failed to read Trivy license data")


def _trivy_license_dict_to_license_map(
    data: TrivyLicenseDict,
) -> tuple[dict[Path, str], set[Path]]:
    license_map: dict[Path, str] = {}
    invalid: set[Path] = set()
    for result in data.get("Licenses", []):
        path = Path(result["FilePath"])
        name = result["Name"]
        # Sometimes trivy returns names that aren't valid SPDX expressions.
        # Treat them as undetected license files in that case.
        if not validate_license(name):
            invalid.add(path)
        # License files can have multiple matches in trivy
        if path in license_map:
            license_map[path] = str(
                combine_licenses(
                    license_map[path],
                    name,
                    validate=False,
                    strict=False,
                )
            )
        else:
            license_map[path] = name
    return license_map, invalid


class TrivyLicenseDetector(LicenseDetector[TrivyLicenseData]):
    NAME = "trivy"
    PACKAGES_NEEDED = ("trivy",)
    FIND_PACKAGES_NEEDED = PACKAGES_NEEDED

    def __init__(
        self,
        detector_config: dict[str, str],
        license_config: LicenseConfig,
        find_only: bool = False,
    ) -> None:
        self._find_only = find_only
        if path := detector_config.get("trivy_path"):
            if not Path(path).exists():
                raise LicenseDetectorNotAvailableError(f"{path!r} does not exist!")
        else:
            path = shutil.which("trivy")
        if not path:
            raise LicenseDetectorNotAvailableError("Failed to find trivy binary!")

        self.path: str = path
        self.detector_config = detector_config
        self.license_config = license_config

    # TODO(anyone): Consider splitting into separate functions
    # https://gitlab.com/gotmax23/go-vendor-tools/-/issues/23
    def detect(self, directory: StrPath) -> TrivyLicenseData:
        # FIXME(gotmax23): Don't call get_go_module_dirs() here. Don't assume the file
        # exists.
        reuse_roots = get_go_module_dirs(Path(directory), relative_paths=True)

        data = _load_license_data(self.path, directory)
        licenses = _license_data_to_trivy_license_dict(data)
        license_map, undetected = _trivy_license_dict_to_license_map(licenses)

        manual_license_map, manual_unmatched = get_manual_license_entries(
            self.license_config["licenses"], directory
        )
        license_map |= manual_license_map
        filtered_license_map = filter_license_map(
            license_map,
            self.license_config["exclude_directories"],
            self.license_config["exclude_files"],
        )
        license_file_lists = find_license_files(
            directory,
            relative_paths=True,
            exclude_directories=self.license_config["exclude_directories"],
            exclude_files=self.license_config["exclude_files"],
            reuse_roots=reuse_roots,
            # FIXME(gotmax23): Also include LICENSE_FILE_TYPE and make sure
            # that find_license_files does not find any license files that
            # trivy did not detect
            filetype_info=[NOTICE_FILE_TYPE],
        )
        filtered_license_map |= reuse_path_to_license_map(license_file_lists["reuse"])
        filtered_license_map = dict(
            sorted(filtered_license_map.items(), key=lambda item: item[0])
        )
        return TrivyLicenseData(
            directory=Path(directory),
            license_map=filtered_license_map,
            undetected_licenses=undetected,
            unmatched_extra_licenses=manual_unmatched,
            trivy_license_data=licenses,
            # FIXME(gotmax): Change the design of LicenseData to not require full paths
            extra_license_files=[
                Path(directory, file) for file in license_file_lists["notice"]
            ],
        )

    def find_license_files(self, directory: StrPath) -> list[Path]:
        # FIXME(gotmax23): Don't call get_go_module_dirs() here. Don't assume the file
        # exists.
        reuse_roots = get_go_module_dirs(Path(directory), relative_paths=True)

        data = _load_license_data(self.path, directory)
        licenses = _license_data_to_trivy_license_dict(data)
        license_map, undetected = _trivy_license_dict_to_license_map(licenses)
        filtered_license_map = filter_license_map(
            license_map,
            self.license_config["exclude_directories"],
            self.license_config["exclude_files"],
        )
        manual_license_map, _ = get_manual_license_entries(
            self.license_config["licenses"], directory
        )
        license_file_lists = find_license_files(
            directory,
            relative_paths=True,
            exclude_directories=self.license_config["exclude_directories"],
            exclude_files=self.license_config["exclude_files"],
            reuse_roots=reuse_roots,
            filetype_info=[NOTICE_FILE_TYPE],
        )
        files: set[Path] = {
            *filtered_license_map.keys(),
            *undetected,
            *manual_license_map,
            *map(Path, chain.from_iterable(license_file_lists.values())),
        }
        return sorted(files)
