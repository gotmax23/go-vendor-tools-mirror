# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

from __future__ import annotations

import re
import sys
from io import StringIO
from pathlib import Path
from shutil import copy2
from textwrap import dedent

import pytest
from pytest_mock import MockerFixture

from go_vendor_tools.cli import go_vendor_license, utils
from go_vendor_tools.config.base import BaseConfig
from go_vendor_tools.exceptions import MissingDependencyError
from go_vendor_tools.license_detection.base import (
    LicenseData,
    LicenseDetectorNotAvailableError,
)

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def test_need_tomlkit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(utils, "HAS_TOMLKIT", False)
    with pytest.raises(
        MissingDependencyError,
        match=re.escape("tomlkit is required for this action. Please install it!"),
    ):
        go_vendor_license.need_tomlkit()


def test_choose_license_detector_error_1(
    monkeypatch: pytest.MonkeyPatch, config1: BaseConfig
) -> None:
    monkeypatch.setattr(
        "go_vendor_tools.license_detection.scancode.HAS_SCANCODE", False
    )
    with pytest.raises(
        SystemExit,
        match="Failed to get detector 'scancode':"
        " The scancode-toolkit library must be installed!",
    ):
        go_vendor_license.choose_license_detector(
            "scancode", config1["licensing"], None
        )


def test_choose_license_detector_error_2(
    mocker: MockerFixture, capsys: pytest.CaptureFixture, config1: BaseConfig
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
        go_vendor_license.choose_license_detector(None, config1["licensing"], None)
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
            Path("LICENSE.unknown"): "Unknown",
            Path("vendor/xyz/COPYING"): "GPL-3.0-only",
        },
        undetected_licenses=frozenset(
            {
                Path("LICENSE.undetected"),
                Path("vendor/123/COPYING.123"),
            }
        ),
        unmatched_manual_licenses=(
            Path("LICENSE-Custom"),
            Path("vendor/custom/LICENSE"),
        ),
        extra_license_files=(),
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
    LICENSE.unknown: Unknown
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

    GPL-3.0-only AND MIT AND Unknown

    The following license keys are NOT RECOGNIZED:
    - Unknown
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
