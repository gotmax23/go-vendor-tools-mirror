# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

from __future__ import annotations

import pytest

from go_vendor_tools.licensing import (
    combine_licenses,
    compare_licenses,
    simplify_license,
)


@pytest.mark.parametrize(
    "expression, expected",
    [
        pytest.param("GPL-2.0-only", "GPL-2.0-only"),
        pytest.param("GPL-2.0-only OR GPL-2.0", "GPL-2.0-only"),
        pytest.param(
            "(MIT OR Apache-2.0) AND Apache-2.0",
            "Apache-2.0 AND (Apache-2.0 OR MIT)",
        ),
        pytest.param(
            "(Apache-2.0 OR MIT) AND Apache-2.0",
            "Apache-2.0 AND (Apache-2.0 OR MIT)",
        ),
        pytest.param(
            "(Apache-2.0 AND (MIT OR Apache-2.0)) AND Apache-2.0",
            "Apache-2.0 AND (Apache-2.0 OR MIT)",
        ),
    ],
)
def test_simplify_license(expression: str, expected: str) -> None:
    simplified = simplify_license(expression)
    assert str(simplified) == expected
    assert compare_licenses(expected, simplified)


def test_combine_licenses() -> None:
    combined = combine_licenses("Apache-2.0 OR MIT", "ISC")
    assert str(combined) == "ISC AND (Apache-2.0 OR MIT)"
