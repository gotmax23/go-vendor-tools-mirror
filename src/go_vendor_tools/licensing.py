# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Utilities for working with license expressions
"""

from __future__ import annotations

import license_expression
from boolean.boolean import DualBase

licensing = license_expression.get_spdx_licensing()


def combine_licenses(
    *expressions: str | license_expression.LicenseExpression | None,
    validate=True,
    strict=True,
) -> license_expression.LicenseExpression:
    """
    Combine SPDX license expressions with AND
    """
    # Set a file's license to an empty string or None to exclude it from the
    # calculation.
    filtered = [str(expression) for expression in expressions if expression]
    filtered.sort()
    return simplify_license(
        str(license_expression.combine_expressions(filtered, licensing=licensing)),
        validate=validate,
        strict=strict,
    )


def _sort_expression_recursive(
    parsed: license_expression.LicenseExpression, /
) -> license_expression.LicenseExpression:
    if isinstance(parsed, DualBase) and (args := getattr(parsed, "args", None)):
        rec_sorted = sorted((_sort_expression_recursive(arg) for arg in args))
        parsed = parsed.__class__(*rec_sorted)
    return parsed


def simplify_license(
    expression: str | license_expression.LicenseExpression,
    *,
    validate: bool = True,
    strict: bool = True,
) -> str:
    """
    Simplify and verify a license expression
    """
    parsed = licensing.parse(str(expression), validate=validate, strict=strict)
    # DualBase subclasses are collections of licenses with an "AND" or an "OR"
    # relationship.
    if not isinstance(parsed, DualBase):
        return str(parsed)
    # Flatten licenses (e.g., "(MIT AND ISC) AND MIT" -> "MIT AND ISC"
    parsed = parsed.flatten()
    # Perform further license_expression-specific deduplication
    parsed = licensing.dedup(parsed)
    # Recursively sort AND/OR expressions
    parsed = _sort_expression_recursive(parsed)
    return str(parsed)


def compare_licenses(
    license1: license_expression.LicenseExpression | str,
    license2: str | license_expression.LicenseExpression | str,
    /,
) -> bool:
    return simplify_license(license1) == simplify_license(license2)
