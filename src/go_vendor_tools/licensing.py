# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Utilities for working with license expressions
"""

from __future__ import annotations

import dataclasses
import json
import subprocess
from collections.abc import Collection
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Any

import license_expression

from go_vendor_tools.config.licenses import LicenseConfig, LicenseEntry
from go_vendor_tools.hashing import verify_hash

if TYPE_CHECKING:
    from _typeshed import StrPath

licensing = license_expression.get_spdx_licensing()


class LicenseError(Exception):
    """
    An issue occured while detecting licenses
    """


def get_askalono_data(directory: StrPath) -> list[dict[str, Any]]:
    """
    Crawl `directory` with askalono and return the serialized JSON representation
    """
    licenses_json = subprocess.run(
        ("askalono", "--format=json", "crawl", directory),
        check=True,
        capture_output=True,
    ).stdout.decode("utf-8")
    licenses = []
    for line in licenses_json.splitlines():
        licensed = json.loads(line)
        licenses.append(licensed)
    return licenses


def get_license_data(
    directory, license_data, allow_undetected: Collection[Path] = frozenset()
) -> tuple[set[str], list[Path], list[dict[str, Any]]]:
    """
    Return a tuple of:

    - `set` of unique license expressions
    - `list[Path]` of license files for which license expressions could not be detected
    - List of dictionaries containing relevant license data from askalono
    """
    licenses: set[str] = set()
    undetected_licenses: list[Path] = []
    filtered_license_data: list[dict[str, Any]] = []
    for licensed in license_data:
        if "/PATENTS" not in licensed["path"] and "/NOTICE" not in licensed["path"]:
            try:
                license_name = licensed["result"]["license"]["name"]
            except KeyError:
                if Path(licensed["path"]) not in allow_undetected:
                    undetected_licenses.append(Path(licensed["path"]))
            else:
                licenses.add(license_name)
                filtered_license_data.append(licensed)
    if not licenses:
        raise FileNotFoundError(f"No license files found in {directory}")
    return licenses, undetected_licenses, filtered_license_data


def get_simplified_license_map(
    filtered_license_data: list[dict[str, Any]],
    extra_license_mapping: dict[Path, str] | None = None,
) -> dict[Path, str]:
    """
    Given license data from askalono, return a simple mapping of license file
    Path to the license expression
    """
    results: dict[Path, str] = {}
    for licensed in filtered_license_data:
        license_name = licensed["result"]["license"]["name"]
        license_path = Path(licensed["path"])
        results[license_path] = license_name
    results.update(extra_license_mapping or {})
    return dict(sorted(results.items(), key=lambda item: item[0]))


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


def combine_licenses(*expressions: str) -> license_expression.LicenseExpression:
    return license_expression.combine_expressions(
        expressions, licensing=licensing
    ).simplify()


def simplify_license(expression: str) -> str:
    return str(licensing.parse(expression, validate=True, strict=True).simplify())


def compare_licenses(
    simplified_expression: license_expression.LicenseExpression,
    expression_str: str,
    /,
) -> bool:
    expression2 = licensing.parse(expression_str).simplify()
    return simplified_expression == expression2


def get_license_file_paths(directory: Path, config: LicenseConfig) -> list[Path]:
    results = get_license_results(directory, config)

    r = [
        directory / lic
        for lic in chain(results.simplified_license_map, results.undetected_licenses)
    ]
    return r


@dataclasses.dataclass()
class LicenseResults:
    """
    Attributes:
        licenses:
            Set of license identifiers
        license_expression:
            Simplified SPDX expression
        askalono_data:
            License JSON data created by `askalono crawl`
        filtered_license_data:
            License JSON data with irrelevant files filtered
        simplified_license_map:
            Simplified mapping of license file `Path`s to license identifiers
        undetected_licenses:
            License files that could not be detected by askalono
        unmatched_extra_licenses:
            Licenses from the `LicenseConfig` that did not match any licenses
            in the project directory
    """

    licenses: set[str]
    license_expression: str
    askalono_data: list[dict[str, Any]]
    filtered_license_data: list[dict[str, Any]]
    simplified_license_map: dict[Path, str]
    undetected_licenses: list[Path]
    unmatched_extra_licenses: list[Path]


def get_license_results(directory: Path, config: LicenseConfig) -> LicenseResults:
    license_data = get_askalono_data(directory)
    extra_licenses, not_matched = get_extra_licenses(config["licenses"])
    licenses, undetected_licenses, filtered_license_data = get_license_data(
        directory, license_data, extra_licenses
    )
    simplified_license_map = get_simplified_license_map(
        filtered_license_data, extra_licenses
    )
    expression = combine_licenses(*licenses)
    return LicenseResults(
        licenses=licenses,
        license_expression=expression,
        askalono_data=license_data,
        filtered_license_data=filtered_license_data,
        simplified_license_map=simplified_license_map,
        undetected_licenses=undetected_licenses,
        unmatched_extra_licenses=not_matched,
    )
