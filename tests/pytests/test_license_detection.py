# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
from pathlib import Path
from subprocess import CalledProcessError
from typing import Any

import pytest
from pytest_mock import MockerFixture

from go_vendor_tools.config.base import BaseConfig, load_config
from go_vendor_tools.license_detection.askalono import AskalonoLicenseDetector
from go_vendor_tools.license_detection.base import (
    LicenseData,
    LicenseDetector,
    get_manual_license_entries,
)
from go_vendor_tools.license_detection.load import DETECTORS
from go_vendor_tools.license_detection.trivy import TrivyLicenseDetector


def test_get_extra_licenses(test_data: Path) -> None:
    case_dir = test_data / "case1"
    licenses_dir = case_dir / "licenses"
    config = load_config(case_dir / "config.toml")
    matched, missing = get_manual_license_entries(
        config["licensing"]["licenses"], licenses_dir
    )
    expected_map = {
        Path("LICENSE.BSD3"): "BSD-3-Clause",
        Path("LICENSE.MIT"): "MIT",
    }
    assert matched == expected_map
    assert not missing


def test_get_extra_licenses_error(test_data: Path, config1_broken: BaseConfig) -> None:
    case_dir = test_data / "case1"
    licenses_dir = case_dir / "licenses"
    matched, missing = get_manual_license_entries(
        config1_broken["licensing"]["licenses"], licenses_dir
    )
    expected_map = {Path("LICENSE.BSD3"): "BSD-3-Clause"}
    assert matched == expected_map
    assert missing == (Path("LICENSE.MIT"),)


@pytest.mark.parametrize(
    "case_name, allowed_detectors, cli_config",
    [
        pytest.param("case2", None, {}, id="case2"),
        pytest.param("case3", [AskalonoLicenseDetector], {"multiple": "1"}, id="case3"),
    ],
)
def test_load_dump_license_data(
    test_data: Path,
    detector: type[LicenseDetector],
    case_name: str,
    allowed_detectors: list[type[LicenseDetector]] | None,
    cli_config: dict[str, str],
    mocker: MockerFixture,
) -> None:
    if allowed_detectors is not None and detector not in allowed_detectors:
        pytest.skip(f"{case_name} does use {detector}")

    # Needed for case3
    mocker.patch("go_vendor_tools.gomod.get_go_module_names", return_value={"abc": ""})

    case_dir = test_data / case_name
    expected_report = case_dir / "reports" / f"{detector.NAME}.json"
    licenses_dir = case_dir / "licenses"
    config = load_config(case_dir / "go-vendor-tools.toml", allow_missing=True)
    detector_obj = detector(cli_config, config["licensing"])
    try:
        data: LicenseData = detector_obj.detect(licenses_dir, ("vendor/abc",))
    except Exception as exc:
        print(exc)
        if isinstance(exc, CalledProcessError):
            print("stdout:", exc.stdout)
            print("stderr:", exc.stderr)
            if case_name == "case3" and "Found argument '--multiple'" in exc.stderr:
                # stderr: error: Found argument '--multiple' which wasn't
                # expected, or isn't valid in this context
                # For some reason, this only happens on EL 9.
                pytest.xfail()
        raise

    placeholder_path = Path("/placeholder")
    data = data.replace(directory=placeholder_path)

    jsonable = data.to_jsonable()
    new_data = type(data).from_jsonable(jsonable)
    assert new_data.to_jsonable() == jsonable

    _remove_license_scanner_data(jsonable)
    # NOTE: Uncomment this line to regenerate the test fixtures
    # (expected_report).write_text(json.dumps(jsonable, indent=2) + "\n")
    with (expected_report).open() as fp:
        gotten_json = _remove_license_scanner_data(json.load(fp))
    assert gotten_json == jsonable


def _remove_license_scanner_data(data: dict[str, Any]) -> dict[str, Any]:
    """
    Remove license-scanner specific data from license data dict, as this data
    tends to be unstable and change between versions.
    We only care about the data that's actually produced by g-v-t.
    """
    for name in DETECTORS:
        key = f"{name}_license_data"
        data.pop(key, None)
    return data


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


def test_detect_files(detector: type[LicenseDetector], test_data: Path) -> None:
    if detector is TrivyLicenseDetector:
        pytest.skip("trivy is not supported")
    config = load_config(None)
    detector_obj = detector({}, config["licensing"])
    case1 = test_data / "case1/licenses"
    files = [
        case1 / "LICENSE.BSD3",
        case1 / "LICENSE.MIT",
        test_data / "case2/licenses/LICENSE.undetected",
    ]
    files = [path.relative_to(test_data) for path in files]
    mapping, undetected = detector_obj.detect_files(files, test_data)
    expected_mapping = {
        Path("case1/licenses/LICENSE.BSD3"): "BSD-3-Clause",
        Path("case1/licenses/LICENSE.MIT"): "MIT",
    }
    expected_undetected = {Path("case2/licenses/LICENSE.undetected")}
    assert mapping == expected_mapping
    assert undetected == expected_undetected


def test_detect_files_absolute(
    detector: type[LicenseDetector], test_data: Path
) -> None:
    if detector is TrivyLicenseDetector:
        pytest.skip("trivy is not supported")
    config = load_config(None)
    detector_obj = detector({}, config["licensing"])
    case1 = test_data / "case1/licenses"
    files = [
        case1 / "LICENSE.BSD3",
        case1 / "LICENSE.MIT",
        test_data / "case2/licenses/LICENSE.undetected",
    ]
    mapping, undetected = detector_obj.detect_files(files)
    expected_mapping = {
        files[0]: "BSD-3-Clause",
        files[1]: "MIT",
    }
    expected_undetected = {files[2]}
    assert mapping == expected_mapping
    assert undetected == expected_undetected
