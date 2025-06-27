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
from collections.abc import Callable, Collection, Iterable
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict, cast

from license_expression import ExpressionError

from go_vendor_tools.config.utils import str_to_bool
from go_vendor_tools.exceptions import LicenseError

from ..config.licenses import LicenseConfig
from ..licensing import combine_licenses
from .base import (
    LicenseData,
    LicenseDetector,
    LicenseDetectorNotAvailableError,
    get_manual_license_entries,
    is_unwanted_path,
    reuse_path_to_license_map,
)
from .search import find_license_files

if TYPE_CHECKING:
    from _typeshed import StrPath
    from typing_extensions import NotRequired

# Whether to pass --multiple to askalono identify
CONFIG_MULTIPLE_DEFAULT = False


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
    directory: StrPath, relpaths: Iterable[StrPath], multiple: bool = False
) -> list[AskalonoLicenseDict]:
    stdin = "\n".join(map(str, relpaths))
    cmd = [
        "askalono",
        "--format",
        "json",
        "identify",
        "--batch",
    ]
    # --multiple seems to cause some licenses to not be detected at all, so
    # gate this behind a flag
    if multiple:
        cmd.append("--multiple")
    licenses_json = subprocess.run(
        cmd,
        input=stdin,
        check=True,
        capture_output=True,
        text=True,
        cwd=directory,
    ).stdout
    licenses = [
        _filter_path(cast(AskalonoLicenseDict, json.loads(line)))
        for line in sorted(licenses_json.splitlines())
    ]
    licenses.sort(key=lambda ld: ld.get("path", ""))
    return licenses


def _get_relative(base_dir: Path | None, file: str | Path) -> Path:
    file = Path(file)
    return (
        file.relative_to(base_dir)
        if base_dir is not None and file.is_absolute()
        else file
    )


def _get_license_name(
    data: AskalonoLicenseDict,
    check: bool,  # noqa: ARG001
) -> str | None:
    name: str | None = None
    if "result" not in data:
        pass
    elif con := data["result"]["containing"]:
        try:
            name = combine_licenses(
                *(entry["license"]["name"] for entry in con),
                # NOTE(gotmax): Always disable this for now.
                # Later code checks for invalid license expressions and reports
                # failures in a nicer way, even if it looses the context of
                # where the errors were found.
                validate=False,
                strict=False,
                # validate=check,
                # strict=check,
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
    directory: Path | None,
) -> tuple[list[AskalonoLicenseDict], set[Path]]:

    undetected_licenses: set[Path] = set()
    results: list[AskalonoLicenseDict] = []

    for licensed in data:
        if _get_license_name(licensed, False):
            results.append(licensed)
        else:
            undetected_licenses.add(_get_relative(directory, licensed["path"]))
    return results, undetected_licenses


def _get_simplified_license_map(
    directory: Path | None,
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


@dataclasses.dataclass(frozen=True)
class AskalonoLicenseData(LicenseData):
    askalono_license_data: list[AskalonoLicenseDict]


class AskalonoLicenseDetector(LicenseDetector[AskalonoLicenseData]):
    NAME = "askalono"
    PACKAGES_NEEDED = ("askalono-cli",)

    def __init__(
        self,
        detector_config: dict[str, str],
        license_config: LicenseConfig,
        find_only: bool = False,
    ) -> None:
        self._find_only = find_only
        path: str | None = None
        if self.find_only:
            # If find_only, just set path to something
            path = "askalono"
        else:
            if path := detector_config.get("askalono_path"):
                if not Path(path).exists():
                    raise LicenseDetectorNotAvailableError(f"{path!r} does not exist!")
            else:
                path = shutil.which("askalono")
            if not path:
                raise LicenseDetectorNotAvailableError(
                    "Failed to find askalono binary!"
                )

        self.path: str = path
        self.detector_config = detector_config
        self.license_config = license_config

    def detect(
        self, directory: StrPath, reuse_roots: Collection[StrPath] = ()
    ) -> AskalonoLicenseData:
        if self.find_only:
            raise ValueError(
                "This cannot be called when class was initalized with find_only=True"
            )
        gitignore = Path(directory, ".gitignore")
        if gitignore.is_file():
            _remove_line(gitignore, lambda line: line.startswith("vendor"))
        license_file_lists = find_license_files(
            directory=directory,
            relative_paths=True,
            exclude_directories=self.license_config["exclude_directories"],
            exclude_files=self.license_config["exclude_files"],
            reuse_roots=reuse_roots,
        )
        askalono_license_data = _get_askalono_data(
            directory,
            license_file_lists["license"],
            str_to_bool(self.detector_config.get("multiple"), CONFIG_MULTIPLE_DEFAULT),
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
        license_map |= reuse_path_to_license_map(license_file_lists["reuse"])
        # Sort
        license_map = dict(sorted(license_map.items(), key=lambda item: item[0]))
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
            undetected_licenses=frozenset(undetected),
            unmatched_manual_licenses=manual_unmatched,
            askalono_license_data=askalono_license_data,
            extra_license_files=tuple(map(Path, license_file_lists["notice"])),
            detector_name=self.NAME,
        )

    def detect_files(
        self, files: Iterable[Path], directory: Path | None = None
    ) -> tuple[dict[Path, str], set[Path]]:
        if self.find_only:
            raise ValueError(
                "This cannot be called when class was initalized with find_only=True"
            )
        askalono_license_data = _get_askalono_data(
            directory if directory is not None else "/",
            files,
            str_to_bool(self.detector_config.get("multiple"), CONFIG_MULTIPLE_DEFAULT),
        )
        filtered_license_data, undetected = _filter_license_data(
            askalono_license_data, directory
        )
        license_map = _get_simplified_license_map(directory, filtered_license_data, {})
        return license_map, undetected
