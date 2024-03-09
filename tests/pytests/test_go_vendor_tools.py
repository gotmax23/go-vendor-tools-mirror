# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

from __future__ import annotations

import sys
from pathlib import Path
from shutil import copy2

import pytest

from go_vendor_tools.cli import go_vendor_license
from go_vendor_tools.config.base import load_config
from go_vendor_tools.license_detection.base import (
    LicenseData,
    LicenseDetector,
    get_extra_licenses,
)
from go_vendor_tools.license_detection.load import get_detctors

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

HERE = Path(__file__).resolve().parent
TEST_DATA = HERE / "test_data"

CONFIG1 = load_config(TEST_DATA / "case1" / "config.toml")
CONFIG1_BROKEN = load_config(TEST_DATA / "case1" / "config-broken.toml")


def get_available_detectors() -> list[type[LicenseDetector]]:
    # TODO(anyone): Allow enforcing "strict mode" if any detectors are missing
    # This can be a env var and then enabled in the noxfile.
    available, missing = get_detctors({}, CONFIG1["licensing"])
    # HACK: We initialize the classes using a test config to check if they are
    # available and then return the base class so that it can be reinitialized
    return [type(d) for d in available.values()]


@pytest.fixture(name="detector", params=get_available_detectors())
def get_detectors(request) -> type[LicenseDetector]:
    return request.param


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
    matched, missing = get_extra_licenses(config["licensing"]["licenses"], licenses_dir)
    expected_map = {
        Path("LICENSE.BSD3"): "BSD-3-Clause",
        Path("LICENSE.MIT"): "MIT",
    }
    assert matched == expected_map
    assert not missing


def test_get_extra_licenses_error(test_data: Path) -> None:
    case_dir = test_data / "case1"
    licenses_dir = case_dir / "licenses"
    matched, missing = get_extra_licenses(
        CONFIG1_BROKEN["licensing"]["licenses"], licenses_dir
    )
    expected_map = {Path("LICENSE.BSD3"): "BSD-3-Clause"}
    assert matched == expected_map
    assert missing == [Path("LICENSE.MIT")]


def test_load_dump_license_data(
    test_data: Path, detector: type[LicenseDetector]
) -> None:
    case_dir = test_data / "case2"
    licenses_dir = case_dir / "licenses"
    config = load_config(None)
    detector_obj = detector({}, config["licensing"])
    data: LicenseData = detector_obj.detect(licenses_dir)
    jsonable = data.to_jsonable()
    new_data = type(data).from_jsonable(jsonable)
    assert new_data.to_jsonable() == jsonable


def test_detect_nothing(tmp_path: Path, detector: type[LicenseDetector]) -> None:
    """
    Ensure the code has proper error handling for when no licenses are detected
    """
    config = load_config(None)
    detector_obj = detector({}, config["licensing"])
    data: LicenseData = detector_obj.detect(tmp_path)
    assert data.directory == tmp_path
    assert not data.license_map
    assert not data.undetected_licenses
    assert not data.license_set
    assert data.license_expression is None
