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
from go_vendor_tools.licensing import combine_licenses, get_extra_licenses

from .base import LicenseData, LicenseDetector, LicenseDetectorNotAvailableError

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

    # TODO: Consider splitting into separate functions
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
        for result in licenses["Licenses"]:
            path = Path(result["FilePath"])
            name = result["Name"]
            # License files can have multiple matches in trivy
            if path in license_map:
                license_map[path] = str(combine_licenses(license_map[path], name))
            else:
                license_map[path] = name

            extra, unmatched = get_extra_licenses(self.license_config["licenses"])
            license_map |= extra

        return TrivyLicenseData(
            directory=Path(directory),
            license_map=dict(sorted(license_map.items(), key=lambda item: item[0])),
            # Trivy doesn't include undetected_licenses
            undetected_licenses=[],
            unmatched_extra_licenses=unmatched,
            trivy_license_data=licenses,
        )
