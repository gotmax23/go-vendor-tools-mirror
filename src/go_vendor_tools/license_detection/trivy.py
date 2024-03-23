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
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, TypedDict, cast

from go_vendor_tools.config.licenses import LicenseConfig
from go_vendor_tools.licensing import combine_licenses

from .base import (
    LicenseData,
    LicenseDetector,
    LicenseDetectorNotAvailableError,
    filter_license_map,
    find_extra_license_files,
    get_extra_licenses,
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


class TrivyLicenseDetector(LicenseDetector[TrivyLicenseData]):
    NAME = "trivy"
    PACKAGES_NEEDED = ("trivy",)

    def __init__(
        self, cli_config: dict[str, str], license_config: LicenseConfig
    ) -> None:
        if path := cli_config.get("trivy_path"):
            if not Path(path).exists():
                raise LicenseDetectorNotAvailableError(f"{path!r} does not exist!")
        else:
            path = shutil.which("trivy")
        if not path:
            raise LicenseDetectorNotAvailableError("Failed to find trivy binary!")

        self.path: str = path
        self.license_config = license_config

    # TODO(anyone): Consider splitting into separate functions
    # https://gitlab.com/gotmax23/go-vendor-tools/-/issues/23
    def detect(self, directory: StrPath) -> TrivyLicenseData:
        # fmt: off
        cmd = [
            self.path,
            "fs",
            "--scanners", "license",
            "--license-full",
            "-f", "json",
            directory,
        ]
        # fmt: on
        data = run_read_json(cmd)
        for item in data["Results"]:
            if item.get("Class") == "license-file":
                licenses = cast(TrivyLicenseDict, item)
                break
        else:
            raise ValueError("Failed to read Trivy license data")

        license_map: dict[Path, str] = {}
        for result in licenses.get("Licenses", []):
            path = Path(result["FilePath"])
            name = result["Name"]
            # License files can have multiple matches in trivy
            if path in license_map:
                license_map[path] = str(
                    combine_licenses(
                        # No need to validate. We do that later.
                        license_map[path],
                        name,
                        validate=False,
                        strict=False,
                    )
                )
            else:
                license_map[path] = name

        extra, unmatched = get_extra_licenses(
            self.license_config["licenses"], directory
        )
        license_map |= extra
        filtered_license_map = filter_license_map(
            license_map,
            self.license_config["exclude_directories"],
            self.license_config["exclude_files"],
        )
        filtered_license_map = dict(
            sorted(filtered_license_map.items(), key=lambda item: item[0])
        )

        extra_license_files = list(
            find_extra_license_files(
                directory,
                self.license_config["exclude_directories"],
                self.license_config["exclude_files"],
            )
        )
        return TrivyLicenseData(
            directory=Path(directory),
            license_map=filtered_license_map,
            # Trivy doesn't include undetected_licenses
            undetected_licenses=[],
            unmatched_extra_licenses=unmatched,
            trivy_license_data=licenses,
            extra_license_files=extra_license_files,
        )
