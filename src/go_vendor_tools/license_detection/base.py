# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Base classes for handling license detection tools
"""

from __future__ import annotations

import abc
import dataclasses
from collections.abc import Collection
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar

import license_expression

from go_vendor_tools.config.licenses import LicenseConfig, LicenseEntry
from go_vendor_tools.exceptions import LicenseError
from go_vendor_tools.hashing import verify_hash
from go_vendor_tools.licensing import combine_licenses

if TYPE_CHECKING:
    from _typeshed import StrPath


def get_extra_licenses(
    licenses: list[LicenseEntry], directory: StrPath
) -> tuple[dict[Path, str], list[Path]]:
    results: dict[Path, str] = {}
    not_matched: list[Path] = []
    seen: set[Path] = set()
    for lic in licenses:
        path = Path(directory, lic["path"])
        if path in results:
            raise LicenseError(
                f"{path} was specified multiple times in the configuration!"
            )
        seen.add(path)
        if verify_hash(path, lic["sha256sum"]):
            results[path] = lic["expression"]
        else:
            not_matched.append(path)
    return results, not_matched


def is_unwanted_path(
    path: Path,
    exclude_directories: Collection[StrPath],
    exclude_files: Collection[StrPath],
) -> bool:
    return (
        # Hardcoded exception
        "testdata" in path.parts
        or path in exclude_files
        or any(path.is_relative_to(directory) for directory in exclude_directories)
    )


def filter_license_map(
    license_map: dict[Path, str],
    exclude_directories: Collection[StrPath],
    exclude_files: Collection[StrPath],
) -> dict[Path, str]:
    """
    Filter licenses files from unwanted paths
    """
    exclude_directories = set(exclude_directories)
    exclude_files = {Path(file) for file in exclude_files}
    return {
        path: exp
        for path, exp in license_map.items()
        if not is_unwanted_path(path, exclude_directories, exclude_files)
    }


@dataclasses.dataclass()
class LicenseData:
    """
    Generic class representing detected license data.
    Can be subclassed by detector implementations to add additional fields.

    Attributes:
        directory:
            Path that was crawled for licensed
        license_map:
            Mapping of relative paths to license (within `directory`) to str
            SPDX license expressions
        undetected_licenses:
            License files that the license detector implementation failed to
            detect
        license_set:
            Set of unique detected license expressions
        license_expression:
            Cumulative `license_expression.LicenseExpression` SPDX expression
    """

    directory: Path
    license_map: dict[Path, str]
    undetected_licenses: Collection[Path]
    unmatched_extra_licenses: Collection[Path]
    # TODO: Make these into cached_properties
    license_set: set[str] = dataclasses.field(init=False)
    license_expression: license_expression.LicenseExpression | None = dataclasses.field(
        init=False
    )
    license_file_paths: Collection[Path] = dataclasses.field(init=False)
    _LIST_PATH_FIELDS: ClassVar = (
        "undetected_licenses",
        "unmatched_extra_licenses",
        "license_file_paths",
    )
    replace = dataclasses.replace

    def __post_init__(self) -> None:
        self.license_set = set(self.license_map.values())
        self.license_expression = (
            combine_licenses(*self.license_set) if self.license_map else None
        )
        self.license_file_paths = tuple(
            self.directory / lic
            for lic in chain(self.license_map, self.undetected_licenses)
        )

    # TODO: Consider cattrs or pydantic
    def to_jsonable(self) -> dict[str, Any]:
        data = dataclasses.asdict(self)
        for key, value in data.items():
            if key == "directory":
                data[key] = str(value)
            elif key == "license_map":
                data[key] = {str(key1): value1 for key1, value1 in value.items()}
            elif key in (
                "undetected_licenses",
                "unmatched_extra_licenses",
                "license_file_paths",
            ):
                data[key] = list(map(str, value))
            elif key == "license_set":
                data[key] = list(value)
            elif key == "license_expression":
                data[key] = str(value)
        return data

    @classmethod
    def _from_jsonable_to_dict(cls, data: dict[Any, Any]) -> dict[Any, Any]:
        init_fields = [field.name for field in dataclasses.fields(cls) if field.init]
        newdata: dict[Any, Any] = {}
        for key, value in data.items():
            if key not in init_fields:
                continue
            if key == "directory":
                newdata[key] = Path(value)
            elif key == "license_map":
                newdata[key] = {Path(key1): value1 for key1, value1 in value.items()}
            elif key in cls._LIST_PATH_FIELDS:
                newdata[key] = tuple(map(Path, value))
            else:
                newdata[key] = value
        return newdata

    @classmethod
    def from_jsonable(cls: type[LicenseDataT], data: dict[Any, Any]) -> LicenseDataT:
        return cls(**cls._from_jsonable_to_dict(data))


LicenseDataT = TypeVar("LicenseDataT", bound=LicenseData)


class LicenseDetector(Generic[LicenseDataT], metaclass=abc.ABCMeta):
    NAME: ClassVar[str]
    PACKAGES_NEEDED: ClassVar[tuple[str, ...]] = ()

    @abc.abstractmethod
    def __init__(
        self, cli_config: dict[str, str], license_config: LicenseConfig
    ) -> None: ...
    @abc.abstractmethod
    def detect(self, directory: StrPath) -> LicenseDataT: ...


class LicenseDetectorNotAvailableError(LicenseError):
    """
    Failed to load the requested license detector
    """
