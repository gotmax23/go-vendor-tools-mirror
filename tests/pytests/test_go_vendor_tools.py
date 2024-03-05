# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

from __future__ import annotations

import sys
from pathlib import Path
from shutil import copy2

from go_vendor_tools.cli import go_vendor_license
from go_vendor_tools.config.base import load_config
from go_vendor_tools.license_detection.base import get_extra_licenses

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def test_license_explicit(test_data: Path, tmp_path: Path) -> None:
    case_dir = test_data / "case1"
    licenses_dir = case_dir / "licenses"
    with open(case_dir / "config.toml", "rb") as fp:
        expected = tomllib.load(fp)
    dest = tmp_path / "config.toml"
    copy2(case_dir / "config-broken.toml", dest)
    go_vendor_license.main(
        [
            f"-c{dest}",
            f"-C{licenses_dir}",
            "explicit",
            f"-f{licenses_dir / 'LICENSE.MIT'}",
            "MIT",
        ]
    )
    with open(dest, "rb") as fp:
        gotten = tomllib.load(fp)
    assert gotten == expected


def test_get_extra_licenses(test_data: Path) -> None:
    case_dir = test_data / "case1"
    licenses_dir = case_dir / "licenses"
    config = load_config(case_dir / "config.toml")
    matched, missing = get_extra_licenses(
        config["licensing"]["licenses"], case_dir / "licenses"
    )
    expected_map = {
        licenses_dir / "LICENSE.BSD3": "BSD-3-Clause",
        licenses_dir / "LICENSE.MIT": "MIT",
    }
    assert matched == expected_map
    assert not missing


def test_get_extra_licenses_error(test_data: Path) -> None:
    case_dir = test_data / "case1"
    licenses_dir = case_dir / "licenses"
    config = load_config(case_dir / "config-broken.toml")
    matched, missing = get_extra_licenses(
        config["licensing"]["licenses"], case_dir / "licenses"
    )
    expected_map = {licenses_dir / "LICENSE.BSD3": "BSD-3-Clause"}
    assert matched == expected_map
    assert missing == [licenses_dir / "LICENSE.MIT"]
