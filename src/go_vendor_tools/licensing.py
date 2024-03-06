# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Utilities for working with license expressions
"""

from __future__ import annotations

import license_expression

licensing = license_expression.get_spdx_licensing()


def combine_licenses(*expressions: str | None) -> license_expression.LicenseExpression:
    """
    Combine SPDX license expressions with AND
    """
    # Set a file's license to an empty string or None to exclude it from the
    # calculation.
    filtered = [expression for expression in expressions if expression]
    return license_expression.combine_expressions(
        filtered, licensing=licensing
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
