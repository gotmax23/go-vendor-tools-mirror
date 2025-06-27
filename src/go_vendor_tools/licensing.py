# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Utilities for working with license expressions
"""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache, partial
from typing import Any, cast

import license_expression
from boolean.boolean import DualBase


def get_fedora_licensing() -> license_expression.Licensing:
    """
    Get a Licensing object modifed to prefer the LicenseRef-Fedora-* extensions
    """
    license_index = license_expression.get_license_index()
    public_dict: dict[str, Any] = {
        "key": "LicenseRef-Fedora-Public-Domain",
        "aliases": [],
        "is_exception": False,
    }
    lics: list[dict[str, Any]] = [public_dict]
    for lic in license_index:
        if lic.get("is_deprecated", False) or not lic.get("spdx_license_key"):
            continue
        ld = {
            "key": lic.get("spdx_license_key", ""),
            "aliases": lic.get("other_spdx_license_keys", []),
            "is_exception": lic.get("is_exception", ""),
        }
        if ld["key"].startswith("LicenseRef-scancode-public-"):
            public_dict["aliases"].append(ld["key"])
            public_dict["aliases"].extend(
                a for a in ld["aliases"] if a != public_dict["key"]
            )
            continue
        lics.append(ld)
    return license_expression.load_licensing_from_license_index(lics)


licensing = get_fedora_licensing()


def combine_licenses(
    *expressions: str | license_expression.LicenseExpression | None,
    validate=True,
    strict=True,
    recursive_simplify: bool = True,
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
def parse(
    expression: str | license_expression.LicenseExpression,
    validate: bool = True,
    strict: bool = True,
) -> license_expression.LicenseExpression:
    """
    (Cached) Parse a string into a LicenseExpression object.
    """
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
    parsed = parse(expression, validate=validate, strict=strict)
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


def get_unknown_license_keys(
    expression: str | license_expression.LicenseExpression,
) -> list[str]:
    parsed = parse(expression, validate=False, strict=False)
    return licensing.unknown_license_keys(parsed)


def validate_license(expression: str) -> bool:
    try:
        parse(expression)
    except license_expression.ExpressionError:
        return False
    else:
        return True


def compare_licenses(
    license1: license_expression.LicenseExpression | str,
    license2: str | license_expression.LicenseExpression | str,
    /,
    allow_invalid: bool = True,
) -> bool:
    try:
        return simplify_license(license1, validate=False) == simplify_license(
            license2, validate=False
        )
    except license_expression.ExpressionError:
        if not allow_invalid:
            raise
    return False
