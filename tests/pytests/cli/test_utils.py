# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

from __future__ import annotations

from go_vendor_tools.cli import utils


def test_color_default() -> None:
    assert utils.color_default() is None
    assert utils.color_default({"NO_COLOR": "", "FORCE_COLOR": ""}) is None
    assert utils.color_default({"NO_COLOR": "1"}) is False
    assert utils.color_default({"FORCE_COLOR": "1"}) is True
