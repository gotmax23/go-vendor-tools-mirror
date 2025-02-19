# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Utilities for working with license expressions
"""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache, partial
from typing import cast

import license_expression
from boolean.boolean import DualBase

licensing = license_expression.get_spdx_licensing()


def combine_licenses(
    *expressions: str | license_expression.LicenseExpression | None,
    validate=True,
    strict=True,
    recursive_simplify: bool = False,
) -> str:
    """
    Combine SPDX license expressions with AND
    """
    converter = cast(
        "Callable[[str | license_expression.LicenseExpression], str]",
        (
            partial(simplify_license, validate=False, strict=False)
            if recursive_simplify
            else str
        ),
    )
    # Set a file's license to an empty string or None to exclude it from the
    # calculation.
    filtered = [converter(expression) for expression in expressions if expression]
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


@lru_cache(500)
def _parse(
    expression: str | license_expression.LicenseExpression,
    validate: bool = True,
    strict: bool = True,
) -> license_expression.LicenseExpression:
    return licensing.parse(str(expression), validate=validate, strict=strict)


@lru_cache(500)
def simplify_license(
    expression: str | license_expression.LicenseExpression,
    *,
    validate: bool = True,
    strict: bool = True,
) -> str:
    """
    Simplify and verify a license expression
    """
    parsed = _parse(expression, validate=validate, strict=strict)
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


def validate_license(expression: str) -> bool:
    try:
        _parse(expression)
    except license_expression.ExpressionError:
        return False
    else:
        return True


def compare_licenses(
    license1: license_expression.LicenseExpression | str,
    license2: str | license_expression.LicenseExpression | str,
    /,
) -> bool:
    return simplify_license(license1, validate=False) == simplify_license(
        license2, validate=False
    )
