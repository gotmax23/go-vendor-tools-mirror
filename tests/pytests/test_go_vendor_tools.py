# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path
from shutil import copy2
from textwrap import dedent

import pytest
from pytest_mock import MockerFixture

from go_vendor_tools.cli import go_vendor_license, utils
from go_vendor_tools.config.base import load_config
from go_vendor_tools.exceptions import MissingDependencyError
from go_vendor_tools.license_detection.askalono import AskalonoLicenseDetector
from go_vendor_tools.license_detection.base import (
    LicenseData,
    LicenseDetector,
    LicenseDetectorNotAvailableError,
    get_manual_license_entries,
)
from go_vendor_tools.license_detection.load import get_detectors as gd

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
    available, missing = gd({}, CONFIG1["licensing"])
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
    matched, missing = get_manual_license_entries(
        config["licensing"]["licenses"], licenses_dir
    )
    expected_map = {
        Path("LICENSE.BSD3"): "BSD-3-Clause",
        Path("LICENSE.MIT"): "MIT",
    }
    assert matched == expected_map
    assert not missing


def test_get_extra_licenses_error(test_data: Path) -> None:
    case_dir = test_data / "case1"
    licenses_dir = case_dir / "licenses"
    matched, missing = get_manual_license_entries(
        CONFIG1_BROKEN["licensing"]["licenses"], licenses_dir
    )
    expected_map = {Path("LICENSE.BSD3"): "BSD-3-Clause"}
    assert matched == expected_map
    assert missing == [Path("LICENSE.MIT")]


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
    if allowed_detectors and detector not in allowed_detectors:
        pytest.skip(f"case3 does use {detector}")

    # Needed for case3
    mocker.patch("go_vendor_tools.gomod.get_go_module_names", return_value={"abc": ""})

    case_dir = test_data / case_name
    expected_report = case_dir / "reports" / f"{detector.NAME}.json"
    licenses_dir = case_dir / "licenses"
    config = load_config(None)
    detector_obj = detector(cli_config, config["licensing"])
    data: LicenseData = detector_obj.detect(licenses_dir)

    placeholder_path = Path("/placeholder")
    data.license_file_paths = tuple(
        sorted(
            placeholder_path / path.relative_to(data.directory)
            for path in data.license_file_paths
        )
    )
    data.directory = placeholder_path

    jsonable = data.to_jsonable()
    new_data = type(data).from_jsonable(jsonable)
    new_data.license_file_paths = tuple(
        sorted(
            placeholder_path / path.relative_to(data.directory)
            for path in data.license_file_paths
        )
    )
    assert new_data.to_jsonable() == jsonable

    # (expected_report).write_text(json.dumps(jsonable, indent=2))
    with (expected_report).open() as fp:
        gotten_json = json.load(fp)
    assert gotten_json == jsonable


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


def test_need_tomlkit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(utils, "HAS_TOMLKIT", False)
    with pytest.raises(
        MissingDependencyError,
        match="tomlkit is required for this action. Please install it!",
    ):
        go_vendor_license.need_tomlkit()


def test_choose_license_detector_error_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "go_vendor_tools.license_detection.scancode.HAS_SCANCODE", False
    )
    with pytest.raises(
        SystemExit,
        match="Failed to get detector 'scancode':"
        " The scancode-toolkit library must be installed!",
    ):
        go_vendor_license.choose_license_detector(
            "scancode", CONFIG1["licensing"], None
        )


def test_choose_license_detector_error_2(
    mocker: MockerFixture, capsys: pytest.CaptureFixture
) -> None:
    return_value: tuple[dict, dict] = (
        {},
        {
            "abcd": LicenseDetectorNotAvailableError("acbd is missing!?!?"),
            "123": LicenseDetectorNotAvailableError("123 is missing."),
        },
    )
    gd_mock = mocker.patch(
        "go_vendor_tools.cli.go_vendor_license.get_detectors",
        return_value=return_value,
    )
    with pytest.raises(SystemExit, match="1"):
        go_vendor_license.choose_license_detector(None, CONFIG1["licensing"], None)
    out, err = capsys.readouterr()
    assert err == "Failed to load license detectors:\n"
    expected = """\
    ! abcd: acbd is missing!?!?
    ! 123: 123 is missing.
    """
    assert dedent(expected) == out
    gd_mock.assert_called_once()


def test_red() -> None:
    with StringIO() as stream:
        go_vendor_license.red("This is an error", file=stream)
        value = stream.getvalue()
    assert value == "This is an error\n"
    with StringIO() as stream:
        stream.isatty = lambda: True  # type: ignore
        go_vendor_license.red("This is an error", file=stream)
        value = stream.getvalue()
    assert value == "\033[31mThis is an error\033[0m\n"


def test_print_licenses_all(capsys: pytest.CaptureFixture) -> None:
    directory = Path("/does-not-exist")
    license_data = LicenseData(
        directory=directory,
        license_map={
            Path("LICENSE.md"): "MIT",
            Path("vendor/xyz/COPYING"): "GPL-3.0-only",
        },
        undetected_licenses=[
            Path("LICENSE.undetected"),
            Path("vendor/123/COPYING.123"),
        ],
        unmatched_extra_licenses=[
            Path("LICENSE-Custom"),
            Path("vendor/custom/LICENSE"),
        ],
        extra_license_files=[],
        detector_name="",
    )
    go_vendor_license.print_licenses(
        results=license_data,
        unlicensed_mods=[
            Path("LICENSE.unmatched"),
            Path("vendor/123/456/LICENSE.unmatched1"),
        ],
        mode="all",
        show_undetected=True,
        show_unlicensed=True,
        directory=directory,
    )
    out, err = capsys.readouterr()
    assert not err
    expected = """\
    LICENSE.md: MIT
    vendor/xyz/COPYING: GPL-3.0-only

    The following license files were found but the correct license identifier couldn't be determined:
    - LICENSE.undetected
    - vendor/123/COPYING.123
    The following modules are missing license files:
    - LICENSE.unmatched
    - vendor/123/456/LICENSE.unmatched1
    The following license files that were specified in the configuration have changed:
    - LICENSE-Custom
    - vendor/custom/LICENSE

    GPL-3.0-only AND MIT
    """  # noqa: E501
    assert out == dedent(expected)


def test_generate_buildrequires(capsys: pytest.CaptureFixture):
    go_vendor_license.main(["--detector=askalono", "generate_buildrequires"])
    out, err = capsys.readouterr()
    assert not err
    assert out == "askalono-cli\n"


def test_generate_buildrequires_no_check(capsys: pytest.CaptureFixture):
    go_vendor_license.main(
        ["--detector=askalono", "generate_buildrequires", "--no-check"]
    )
    out, err = capsys.readouterr()
    assert not err
    assert not out


def test_generate_buildrequires_trivy(capsys: pytest.CaptureFixture):
    go_vendor_license.main(["--detector=trivy", "generate_buildrequires"])
    out, err = capsys.readouterr()
    assert not err
    assert out == "trivy\n"


def test_generate_buildrequires_no_check_trivy(capsys: pytest.CaptureFixture):
    go_vendor_license.main(["--detector=trivy", "generate_buildrequires", "--no-check"])
    out, err = capsys.readouterr()
    assert not err
    assert out == "trivy\n"
