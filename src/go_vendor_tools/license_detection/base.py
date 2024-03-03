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
from typing import TYPE_CHECKING, Generic, TypeVar

import license_expression

from go_vendor_tools.config.licenses import LicenseConfig, LicenseEntry
from go_vendor_tools.hashing import verify_hash
from go_vendor_tools.licensing import LicenseError, combine_licenses

if TYPE_CHECKING:
    from _typeshed import StrPath


def get_extra_licenses(
    licenses: list[LicenseEntry],
) -> tuple[dict[Path, str], list[Path]]:
    results: dict[Path, str] = {}
    not_matched: list[Path] = []
    seen: set[Path] = set()
    for lic in licenses:
        path = Path(lic["path"])
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
    license_expression: license_expression.LicenseExpression = dataclasses.field(
        init=False
    )
    license_file_paths: tuple[Path, ...] = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        self.license_set = set(self.license_map.values())
        self.license_expression = combine_licenses(*self.license_set)
        self.license_file_paths = tuple(
            self.directory / lic
            for lic in chain(self.license_map, self.undetected_licenses)
        )


LicenseDataT = TypeVar("LicenseDataT", bound=LicenseData)


class LicenseDetector(Generic[LicenseDataT], metaclass=abc.ABCMeta):
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
