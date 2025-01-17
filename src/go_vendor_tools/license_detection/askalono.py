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
from collections.abc import Callable, Collection
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict, cast

from license_expression import ExpressionError

from go_vendor_tools.exceptions import LicenseError

from ..config.licenses import LicenseConfig
from ..gomod import get_go_module_dirs
from ..licensing import combine_licenses
from .base import (
    LicenseData,
    LicenseDetector,
    LicenseDetectorNotAvailableError,
    get_manual_license_entries,
    is_unwanted_path,
)
from .search import find_license_files

if TYPE_CHECKING:
    from _typeshed import StrPath
    from typing_extensions import NotRequired


class AskalonoLicenseEntry(TypedDict):
    name: str
    kind: str
    aliases: list[str]


class AskalonoLicenseContainingEntry(TypedDict):
    score: float
    license: AskalonoLicenseEntry
    line_range: list[int]


class AskalonoLicenseResult(TypedDict):
    score: float
    license: AskalonoLicenseEntry | None
    containing: list[AskalonoLicenseContainingEntry]


class AskalonoLicenseDict(TypedDict):
    path: str
    result: NotRequired[AskalonoLicenseResult]


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


def _filter_path(data: AskalonoLicenseDict) -> AskalonoLicenseDict:
    data["path"] = data["path"].strip("\n")
    return data


def _get_askalono_data(
    directory: StrPath, relpaths: Collection[StrPath]
) -> list[AskalonoLicenseDict]:
    stdin = "\n".join(map(str, relpaths))
    licenses_json = subprocess.run(
        (
            "askalono",
            "--format",
            "json",
            "identify",
            # TODO(gotmax23): We might want to gate this behind a flag.
            # --multiple seems to cause some licenses to nbot be detected at all.
            # "--multiple",
            "--batch",
        ),
        input=stdin,
        check=True,
        capture_output=True,
        text=True,
        cwd=directory,
    ).stdout
    licenses = [
        _filter_path(cast(AskalonoLicenseDict, json.loads(line)))
        for line in licenses_json.splitlines()
    ]
    return licenses


def _get_relative(base_dir: Path, file: str | Path) -> Path:
    file = Path(file)
    return file.relative_to(base_dir) if file.is_absolute() else file


def _get_license_name(data: AskalonoLicenseDict, check: bool) -> str | None:
    name: str | None = None
    if "result" not in data:
        pass
    elif con := data["result"]["containing"]:
        try:
            name = combine_licenses(
                *(entry["license"]["name"] for entry in con),
                validate=check,
                strict=check,
            )
        except ExpressionError as exc:  # pragma: no cover
            raise LicenseError(
                f"Failed to detect license for {data.get('path')}: {exc}"
            ) from exc
    elif data["result"]["license"]:
        name = data["result"]["license"].get("name")
    return name


def _filter_license_data(
    data: list[AskalonoLicenseDict],
    directory: Path,
) -> tuple[list[AskalonoLicenseDict], set[Path]]:

    undetected_licenses: set[Path] = set()
    results: list[AskalonoLicenseDict] = []

    for licensed in data:
        # TODO(gotmax23): Get rid of this if statement now that we manually crawl for
        # licenses
        if "/PATENTS" not in licensed["path"] and "/NOTICE" not in licensed["path"]:
            if _get_license_name(licensed, False):
                results.append(licensed)
            else:
                undetected_licenses.add(_get_relative(directory, licensed["path"]))
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
        license_name = _get_license_name(licensed, check=True)
        if not license_name:  # pragma: no cover
            raise RuntimeError("Should never get here after filtering the license map")
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
        # FIXME(gotmax23): Don't call get_go_module_dirs() here. Don't assume the file
        # exists.
        reuse_roots = get_go_module_dirs(Path(directory), relative_paths=True)
        license_file_lists = find_license_files(
            directory=directory,
            relative_paths=True,
            exclude_directories=self.license_config["exclude_directories"],
            exclude_files=self.license_config["exclude_files"],
            reuse_roots=reuse_roots,
        )
        askalono_license_data = _get_askalono_data(
            directory, license_file_lists["license"]
        )
        filtered_license_data, undetected = _filter_license_data(
            askalono_license_data, Path(directory)
        )
        manual_license_map, manual_unmatched = get_manual_license_entries(
            self.license_config["licenses"], directory
        )
        license_map = _get_simplified_license_map(
            Path(directory), filtered_license_data, manual_license_map
        )
        # Remove manually specified licenses
        undetected -= set(manual_license_map)
        undetected = {
            path
            for path in undetected
            if not is_unwanted_path(
                path,
                self.license_config["exclude_directories"],
                self.license_config["exclude_files"],
            )
        }
        undetected -= set(manual_license_map)
        return AskalonoLicenseData(
            directory=Path(directory),
            license_map=license_map,
            undetected_licenses=undetected,
            unmatched_extra_licenses=manual_unmatched,
            askalono_license_data=askalono_license_data,
            # TODO(gotmax23): Change the design of LicenseData to not require full paths
            extra_license_files=[
                Path(directory, file) for file in license_file_lists["notice"]
            ],
        )
