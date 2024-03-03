# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Utilities for working with license expressions
"""

from __future__ import annotations

from pathlib import Path

import license_expression

from go_vendor_tools.config.licenses import LicenseEntry
from go_vendor_tools.exceptions import LicenseError
from go_vendor_tools.hashing import verify_hash

licensing = license_expression.get_spdx_licensing()


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
    """
    Combine SPDX license expressions with AND
    """
    return license_expression.combine_expressions(
        expressions, licensing=licensing
    ).simplify()


def simplify_license(expression: str) -> str:
    """
    Simplify and verify a license expression
    """
    return str(licensing.parse(expression, validate=True, strict=True).simplify())


def compare_licenses(
    simplified_expression: license_expression.LicenseExpression, expression_str: str
) -> bool:
    expression2 = licensing.parse(expression_str).simplify()
    return simplified_expression == expression2
