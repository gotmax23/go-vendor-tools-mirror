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
from collections.abc import Collection, Iterable, Sequence
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, TypedDict, cast

from go_vendor_tools.config.licenses import LicenseConfig
from go_vendor_tools.exceptions import LicenseError
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
    is_unwanted_path,
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


@dataclasses.dataclass(frozen=True)
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
    data: TrivyLicenseDict, config: LicenseConfig
) -> tuple[dict[Path, str], set[Path]]:
    license_map: dict[Path, str] = {}
    invalid: set[Path] = set()
    for result in data.get("Licenses", []):
        path = Path(result["FilePath"])
        name = result["Name"]
        if (
            # https://gitlab.com/fedora/sigs/go/go-vendor-tools/-/issues/65
            path.suffix == ".sh"
            or is_unwanted_path(
                path,
                exclude_directories=config["exclude_directories"],
                exclude_files=config["exclude_files"],
            )
        ):
            continue
        # Sometimes trivy returns names that aren't valid SPDX expressions.
        # Treat them as undetected license files in that case.
        if not validate_license(name):
            invalid.add(path)
            continue
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
    def detect(
        self, directory: StrPath, reuse_roots: Collection[StrPath] = ()
    ) -> TrivyLicenseData:
        data = _load_license_data(self.path, directory)
        licenses = _license_data_to_trivy_license_dict(data)
        license_map, undetected = _trivy_license_dict_to_license_map(
            licenses, self.license_config
        )

        manual_license_map, manual_unmatched = get_manual_license_entries(
            self.license_config["licenses"], directory
        )
        undetected -= manual_license_map.keys()
        license_map |= manual_license_map
        license_file_lists = find_license_files(
            directory,
            relative_paths=True,
            exclude_directories=self.license_config["exclude_directories"],
            exclude_files=self.license_config["exclude_files"],
            reuse_roots=reuse_roots,
        )
        license_map |= reuse_path_to_license_map(license_file_lists["reuse"])
        license_map = dict(sorted(license_map.items(), key=lambda item: item[0]))
        # Ensure that any license files found by searching the filesystem
        # manually are detected by trivy
        undetected.update(
            file
            for file in map(Path, license_file_lists["license"])
            if file not in license_map
        )
        return TrivyLicenseData(
            directory=Path(directory),
            license_map=license_map,
            undetected_licenses=frozenset(undetected),
            unmatched_manual_licenses=manual_unmatched,
            trivy_license_data=licenses,
            extra_license_files=tuple(map(Path, license_file_lists["notice"])),
            detector_name=self.NAME,
        )

    def find_license_files(
        self, directory: StrPath, reuse_roots: Collection[StrPath] = ()
    ) -> list[Path]:
        data = _load_license_data(self.path, directory)
        licenses = _license_data_to_trivy_license_dict(data)
        license_map, undetected = _trivy_license_dict_to_license_map(
            licenses, self.license_config
        )
        filtered_license_map = filter_license_map(
            license_map,
            self.license_config["exclude_directories"],
            self.license_config["exclude_files"],
        )
        manual_license_map, unmatched = get_manual_license_entries(
            self.license_config["licenses"], directory
        )
        if unmatched:
            raise LicenseError(
                "Invalid manual license config entries:"
                + "\n"
                + "\n".join(map(str, unmatched)),
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

    def detect_files(
        self, files: Iterable[Path], directory: Path | None = None
    ) -> tuple[dict[Path, str], set[Path]]:
        raise NotImplementedError("The trivy backend does not support detect_files.")
