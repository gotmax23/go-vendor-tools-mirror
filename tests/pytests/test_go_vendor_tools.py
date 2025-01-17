# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

from __future__ import annotations

import sys
from functools import partial
from io import StringIO
from pathlib import Path
from shutil import copy2
from textwrap import dedent

import pytest
from pytest_mock import MockerFixture

from go_vendor_tools.cli import go_vendor_license
from go_vendor_tools.config.base import load_config
from go_vendor_tools.license_detection.base import (
    LicenseData,
    LicenseDetector,
    LicenseDetectorNotAvailableError,
    get_manual_license_entries,
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
    # FIXME(gotmax23): Remove this and fix the tools to not require modules.txt
    (vendor_dir := tmp_path / "vendor").mkdir()
    (vendor_dir / "modules.txt").touch()

    config = load_config(None)
    detector_obj = detector({}, config["licensing"])
    data: LicenseData = detector_obj.detect(tmp_path)
    assert data.directory == tmp_path
    assert not data.license_map
    assert not data.undetected_licenses
    assert not data.license_set
    assert data.license_expression is None


def test_need_tomlkit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(go_vendor_license, "HAS_TOMLKIT", False)
    go_vendor_license.need_tomlkit.cache_clear()
    raise_decorator = partial(
        pytest.raises,
        SystemExit,
        match="tomlkit is required for this action. Please install it!",
    )
    with raise_decorator():
        go_vendor_license.need_tomlkit()
    with raise_decorator():
        go_vendor_license.need_tomlkit()
    go_vendor_license.need_tomlkit.cache_clear()


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
        "go_vendor_tools.cli.go_vendor_license.get_detctors",
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
    # print(out)
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
