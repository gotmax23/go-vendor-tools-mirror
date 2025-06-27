# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Base classes for handling license detection tools
"""

from __future__ import annotations

import abc
import dataclasses
import os
import re
import sys
from collections.abc import Collection, Iterable, Mapping, Sequence
from functools import partial
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Generic

from go_vendor_tools.config.licenses import LicenseConfig, LicenseEntry
from go_vendor_tools.exceptions import LicenseError
from go_vendor_tools.hashing import verify_hash
from go_vendor_tools.license_detection.search import find_license_files
from go_vendor_tools.licensing import combine_licenses, get_unknown_license_keys

if TYPE_CHECKING:
    from _typeshed import StrPath

    # TypeVar from typing_extensions needed for PEP 696
    from typing_extensions import Self, TypeVar
else:
    from typing import TypeVar

EXTRA_LICENSE_FILE_REGEX = re.compile(
    r"^(AUTHORS|NOTICE|PATENTS).*$", flags=re.IGNORECASE
)


def get_manual_license_entries(
    licenses: list[LicenseEntry], directory: StrPath
) -> tuple[dict[Path, str], tuple[Path, ...]]:
    results: dict[Path, str] = {}
    not_matched: list[Path] = []
    seen: set[Path] = set()
    for lic in licenses:
        relpath = Path(lic["path"])
        path = directory / relpath
        if path in results:
            raise LicenseError(
                f"{path} was specified multiple times in the configuration!"
            )
        seen.add(path)
        if verify_hash(path, lic["sha256sum"]):
            results[relpath] = lic["expression"]
        else:
            not_matched.append(relpath)
    return results, tuple(not_matched)


def is_unwanted_path(
    path: Path,
    exclude_directories: Collection[StrPath],
    exclude_files: Collection[str],
) -> bool:
    return (
        # Hardcoded exception
        "testdata" in path.parts
        or str(path) in exclude_files
        or any(path.is_relative_to(directory) for directory in exclude_directories)
    )


def filter_license_map(
    license_map: dict[Path, str],
    exclude_directories: Collection[str],
    exclude_files: Collection[str],
) -> dict[Path, str]:
    """
    Filter licenses files from unwanted paths
    """
    exclude_directories = set(exclude_directories)
    exclude_files = set(exclude_files)
    return {
        path: exp
        for path, exp in license_map.items()
        if not is_unwanted_path(path, exclude_directories, exclude_files)
    }


def python3dist(package: str, /) -> str:
    return f"python{sys.version_info.major}.{sys.version_info.minor}dist({package})"


# TODO(anyone): Should we check for valid filenames
# (each file should be a single license name)
def reuse_path_to_license_map(files: Collection[StrPath]) -> dict[Path, str]:
    result: dict[Path, str] = {}
    for file in files:
        name = os.path.splitext(os.path.basename(file))[0]
        result[Path(file)] = name
    return result


@dataclasses.dataclass(frozen=True)
class LicenseData:
    """
    Generic class representing detected license data.
    Can be subclassed by detector implementations to add additional fields.
    Attributes marked with (Generated fields) are calculated during class init
    and are not passed as values.
    The class is a frozen dataclass and is meant to be (pseudo) immutable.

    Attributes:
        directory:
            Path that was crawled for licensed
        license_map:
            Mapping of relative paths to license (within `directory`) to str
            SPDX license expressions
        undetected_licenses:
            Relative paths of license files that the license detector
            implementation failed to detect
        unmatched_manaul_licenses:
            Relative paths of invalid manually specified license entries
        extra_license_files:
            Relative paths to extra files (e.g., AUTHORS or NOTICE files) that
            we should include in the distribution but not run through the
            license detector
        detector_name:
            Name of the license detector
        license_set:
            (Generated field) Set of unique detected license expressions
        license_expression:
            (Generated field) Cumulative `license_expression.LicenseExpression`
            SPDX expression
        license_files_paths:
            (Generated field) Absolute paths to all detected license files
        unknown_license_keys:
            (Generated field) Unknown license keys in the license_expression.
        is_valid_license:
            (Generated field) Whether license is unknown (i.e., no
            unknown_license_keys)
    """

    directory: Path
    license_map: Mapping[Path, str]
    undetected_licenses: frozenset[Path]
    unmatched_manual_licenses: tuple[Path, ...]
    extra_license_files: tuple[Path, ...]
    detector_name: str

    # Generated fields
    license_set: frozenset[str] = dataclasses.field(init=False, compare=False)
    license_expression: str = dataclasses.field(init=False, compare=False)
    license_file_paths: tuple[Path, ...] = dataclasses.field(init=False, compare=False)
    unknown_license_keys: list[str] = dataclasses.field(init=False, compare=False)
    is_valid_license: bool = dataclasses.field(init=False, compare=False)

    # Helper for *_jsonable() methods
    _LIST_PATH_FIELDS: ClassVar = (
        "undetected_licenses",
        "unmatched_manual_licenses",
        "license_file_paths",
        "extra_license_files",
    )

    # Implement replace() method
    replace = dataclasses.replace

    def __post_init__(self) -> None:
        # Use object.__setattr__ because this is a frozen dataclass.
        object.__setattr__(self, "license_set", frozenset(self.license_map.values()))
        object.__setattr__(
            self,
            "license_expression",
            self._combine_licenses(*self.license_set) if self.license_map else None,
        )
        object.__setattr__(
            self,
            "license_file_paths",
            tuple(
                sorted(
                    self.directory / lic
                    for lic in chain(self.license_map, self.undetected_licenses)
                ),
            ),
        )
        object.__setattr__(
            self,
            "unknown_license_keys",
            get_unknown_license_keys(self.license_expression),
        )
        object.__setattr__(self, "is_valid_license", not self.unknown_license_keys)

    _combine_licenses = staticmethod(
        partial(combine_licenses, validate=False, strict=False)
    )

    # This would be a good task for pydantic, but we want to keep dependencies slim.
    def to_jsonable(self) -> dict[str, Any]:
        data = dataclasses.asdict(self)
        for key, value in data.items():
            if key == "directory":
                data[key] = str(value)
            elif key == "license_map":
                data[key] = {str(key1): value1 for key1, value1 in value.items()}
            elif key in self._LIST_PATH_FIELDS:
                data[key] = list(map(str, value))
                if not isinstance(value, Sequence):
                    data[key].sort()
            elif key == "license_set":
                data[key] = sorted(value)
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
                func = set if key == "undetected_licenses" else tuple
                newdata[key] = func(map(Path, value))
            else:
                newdata[key] = value
        return newdata

    @classmethod
    def from_jsonable(cls, data: dict[Any, Any]) -> Self:
        return cls(**cls._from_jsonable_to_dict(data))


if TYPE_CHECKING:
    _LicenseDataT_co = TypeVar(
        "_LicenseDataT_co", bound=LicenseData, covariant=True, default=LicenseData
    )
else:
    _LicenseDataT_co = TypeVar("_LicenseDataT_co", covariant=True, bound=LicenseData)


class LicenseDetector(Generic[_LicenseDataT_co], metaclass=abc.ABCMeta):
    """
    ABC for a license detector backend

    Attributes:
        NAME: Name of the license detector
        PACKAGES_NEEDED:
            Tuple of Fedora package names needed for the license detector
        FIND_PACKAGES_NEEDED:
            Tuple of packages needed for find_only mode (see __init__ docstring)
        license_config:
            LicenseConfig object passed to the constructor
        detector_config:
            Options passeed to constructor
        find_only: Whether find_only mode is enabled
    """

    NAME: ClassVar[str]
    PACKAGES_NEEDED: ClassVar[tuple[str, ...]] = ()
    FIND_PACKAGES_NEEDED: ClassVar[tuple[str, ...]] = ()
    detector_config: dict[str, str]
    license_config: LicenseConfig
    _find_only: bool

    @abc.abstractmethod
    def __init__(
        self,
        detector_config: dict[str, str],
        license_config: LicenseConfig,
        find_only: bool = False,
    ) -> None:
        """
        Args:
            detector_config:
                String key-value pairs of --detector-config options that are
                defined separately for each license detector implementation
            license_config:
                LicenseConfig object.
                The detector_config option is ignored in favor of the
                detector_config argument.
            find_only:
                When find_only is enabled, only the dependencies for the
                find_license_files method is checked.
                This allows a lightweight mode without the dependencies for the
                detect() method when only a list of valid license files is
                required.
        """

    @property
    def find_only(self):
        """
        Whether find_only mode is enabled.
        """
        return self._find_only

    @abc.abstractmethod
    def detect(
        self, directory: StrPath, reuse_roots: Collection[StrPath] = ...
    ) -> _LicenseDataT_co:
        """
        Scan a directory for license data

        Args:
            directory: Directory
            reuse_roots: Directories to search for REUSE-style LICENSES directory
        """

    @abc.abstractmethod
    def detect_files(
        self, files: Iterable[Path], directory: Path | None = None
    ) -> tuple[dict[Path, str], set[Path]]:
        """
        Given a list of license files, return a mapping of paths to license expressions.

        Args:
            files: List files
            directory:
                Directory to which paths are relative or None to treat as
                absolute paths.

        Returns: (License mapping, undetected files)
        """

    def find_license_files(
        self, directory: StrPath, reuse_roots: Collection[StrPath] = ()
    ) -> list[Path]:
        """
        Default implementation of find_license_files.

        Args:
            directory: Directory
            reuse_roots: Directories to search for REUSE-style LICENSES directory
        Raises:
            LicenseError:
                Invalid manual license config entries are present in the license config
        """
        license_file_lists = find_license_files(
            directory,
            relative_paths=True,
            exclude_directories=self.license_config["exclude_directories"],
            exclude_files=self.license_config["exclude_files"],
            reuse_roots=reuse_roots,
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
        files: set[Path] = {
            Path(p) for p in chain.from_iterable(license_file_lists.values())
        }
        files.update(manual_license_map)
        return sorted(files)


class LicenseDetectorNotAvailableError(LicenseError):
    """
    Failed to load the requested license detector
    """
