# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Detect licenses using askalono
"""

from __future__ import annotations

import dataclasses
import json
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict, cast

from ..config.licenses import LicenseConfig
from .base import (
    LicenseData,
    LicenseDetector,
    LicenseDetectorNotAvailableError,
    filter_license_map,
    find_extra_license_files,
    get_extra_licenses,
    is_unwanted_path,
)

if TYPE_CHECKING:
    from _typeshed import StrPath


class AskalonoLicenseEntry(TypedDict):
    name: str
    kind: str
    aliases: list[str]


class AskalonoLicenseResult(TypedDict):
    score: float
    license: AskalonoLicenseEntry
    containing: list[Any]


class AskalonoLicenseDict(TypedDict):
    path: str
    result: AskalonoLicenseResult


def _remove_line(file: StrPath, key: Callable[[str], bool]) -> None:
    """
    Used to remove vendor directory from .gitignore to avoid confusing askalono
    """
    lines: list[str] = []
    with open(file, "r+", encoding="utf-8") as fp:
        for line in fp:
            if key(line):
                continue
            lines.append(line)
        fp.seek(0)
        fp.writelines(lines)
        fp.truncate()


def _get_askalono_data(directory: StrPath) -> list[AskalonoLicenseDict]:
    """
    Crawl `directory` with askalono and return the serialized JSON representation
    """
    licenses_json = subprocess.run(
        ("askalono", "--format=json", "crawl", directory),
        check=True,
        capture_output=True,
    ).stdout.decode("utf-8")
    licenses = [
        cast(AskalonoLicenseDict, json.loads(line))
        for line in licenses_json.splitlines()
    ]
    return licenses


def _get_relative(base_dir: Path, file: str | Path) -> Path:
    file = Path(file)
    return file.relative_to(base_dir) if file.is_absolute() else file


def _filter_license_data(
    data: list[AskalonoLicenseDict],
    directory: Path,
) -> tuple[list[AskalonoLicenseDict], set[Path]]:

    undetected_licenses: set[Path] = set()
    results: list[AskalonoLicenseDict] = []

    for licensed in data:
        if "/PATENTS" not in licensed["path"] and "/NOTICE" not in licensed["path"]:
            try:
                licensed["result"]["license"]["name"]
            except KeyError:
                undetected_licenses.add(_get_relative(directory, licensed["path"]))
            else:
                results.append(licensed)
    return results, undetected_licenses


def _get_simplified_license_map(
    directory: Path,
    filtered_license_data: list[AskalonoLicenseDict],
    extra_license_mapping: dict[Path, str] | None = None,
) -> dict[Path, str]:
    """
    Given license data from askalono, return a simple mapping of license file
    Path to the license expression
    """
    results: dict[Path, str] = {}
    for licensed in filtered_license_data:
        license_name = licensed["result"]["license"]["name"]
        results[_get_relative(directory, licensed["path"])] = license_name
    results.update(extra_license_mapping or {})
    return dict(sorted(results.items(), key=lambda item: item[0]))


@dataclasses.dataclass()
class AskalonoLicenseData(LicenseData):
    askalono_license_data: list[AskalonoLicenseDict]


class AskalonoLicenseDetector(LicenseDetector[AskalonoLicenseData]):
    NAME = "askalono"
    PACKAGES_NEEDED = ("askalono-cli",)

    def __init__(
        self, cli_config: dict[str, str], license_config: LicenseConfig
    ) -> None:
        if path := cli_config.get("askalono_path"):
            if not Path(path).exists():
                raise LicenseDetectorNotAvailableError(f"{path!r} does not exist!")
        else:
            path = shutil.which("askalono")
        if not path:
            raise LicenseDetectorNotAvailableError("Failed to find askalono binary!")

        self.path: str = path
        self.license_config = license_config

    def detect(self, directory: StrPath) -> AskalonoLicenseData:
        gitignore = Path(directory, ".gitignore")
        if gitignore.is_file():
            _remove_line(gitignore, lambda line: line.startswith("vendor"))
        results, undetected = _filter_license_data(
            _get_askalono_data(directory), Path(directory)
        )
        extra_licenses, unmatched = get_extra_licenses(
            self.license_config["licenses"], directory
        )
        license_map = _get_simplified_license_map(
            Path(directory), results, extra_licenses
        )
        # Remove manually specified licenses
        undetected -= set(extra_licenses)
        undetected = {
            path
            for path in undetected
            if not is_unwanted_path(
                path,
                self.license_config["exclude_directories"],
                self.license_config["exclude_files"],
            )
        }

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
        return AskalonoLicenseData(
            directory=Path(directory),
            license_map=filtered_license_map,
            undetected_licenses=undetected,
            unmatched_extra_licenses=unmatched,
            askalono_license_data=results,
            extra_license_files=extra_license_files,
        )
