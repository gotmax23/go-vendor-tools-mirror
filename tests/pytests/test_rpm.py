# Copyright (C) 2025 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Test of the RPM macros
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import NamedTuple

from go_vendor_tools.config.utils import get_envvar_boolean

PARENT = Path(__file__).resolve().parent.parent.parent
# e.g. MACRO_DIR=%{buildroot}%{_rpmmacrodir} \
#      pytest
# MACRO_DIR="" MACRO_LUA_DIR="" to only use system paths
MACRO_DIR = str(os.environ.get("MACRO_DIR", PARENT / "rpm"))
CHECK_DISABLE_MACRO = "go_vendor_license_check_disable"
# Functionality to force CHECK_DISABLE_MACRO to be disabled so that tests
# behave the same way in Fedora ELN and RHEL that don't run license tests by default.
# This var is set in %check in go-vendor-tools.spec.
FORCE_LICENSE_CHECK_ENABLE = get_envvar_boolean(
    "GVTT_FORCE_LICENSE_CHECK_ENABLE", False
)


class Result(NamedTuple):
    stdout: str
    stderr: str


def macros_path() -> list[str]:
    if MACRO_DIR == "":
        return []
    path = subprocess.run(
        # Don't judge. It works.
        "rpm --showrc | grep 'Macro path' | awk -F ': ' '{print $2}'",
        shell=True,
        text=True,
        check=True,
        capture_output=True,
    ).stdout.strip()
    return ["--macros", f"{path}:{MACRO_DIR}/macros.*"]


class Evaluator:
    def __init__(self) -> None:
        self.macros_path = macros_path()

    def __call__(
        self,
        exps: str | Sequence[str],
        defines: dict[str, str] | None = None,
        undefines: Sequence[str] = (),
        should_fail: bool = False,
        *,
        force_license_check_enable=FORCE_LICENSE_CHECK_ENABLE,
    ) -> Result:
        cmd: list[str] = ["rpm", *self.macros_path]
        if defines is not None:
            defines = defines.copy()
        else:
            defines = {}
        if (
            force_license_check_enable
            and CHECK_DISABLE_MACRO not in defines
            and CHECK_DISABLE_MACRO not in undefines
        ):
            print(f"Setting {CHECK_DISABLE_MACRO} to 0")
            defines[CHECK_DISABLE_MACRO] = "0"
        for name, value in defines.items():
            cmd.extend(("--define", f"{name} {value}"))
        for name in undefines:
            cmd.extend(("--undefine", name))
        if isinstance(exps, str):
            cmd.extend(("-E", exps))
        else:
            for exp in exps:
                cmd.extend(("-E", exp))
        print(cmd)
        proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
        if should_fail:
            assert proc.returncode != 0
        else:
            assert proc.returncode == 0, proc.stderr
        return Result(proc.stdout, proc.stderr)


evaluator = Evaluator()


def test_go_vendor_license_install():
    defines = {"NAME": "foo", "buildroot": "BUILDROOT"}
    assert (
        evaluator("%go_vendor_license_install", defines=defines).stdout
        == "go_vendor_license install --destdir BUILDROOT --install-directory /usr/share/licenses/foo --filelist licenses.list\n"  # noqa: E501
    )


def test_go_vendor_license_install_M():
    defines = {"NAME": "foo", "buildroot": "BUILDROOT"}
    assert (
        evaluator("%go_vendor_license_install -M", defines=defines).stdout
        == "go_vendor_license install --destdir BUILDROOT --install-directory /usr/share/licenses/foo --filelist licenses.list -M\n"  # noqa: E501
    )


def test_go_vendor_license_check_disabled():
    assert not (
        evaluator(
            "%go_vendor_license_check", {"go_vendor_license_check_disable": "1"}
        ).stdout.removesuffix("\n")
    )


def test_go_vendor_license_check_disable_rhel():
    defines = {"rhel": "11"}
    assert (
        evaluator(
            "%go_vendor_license_check_disable",
            defines,
            ["fedora", "epel"],
            force_license_check_enable=False,
        ).stdout
        == "1\n"
    )


def test_go_vendor_license_check_disable_epel():
    defines = {"rhel": "11", "epel": "11"}
    assert (
        evaluator(
            "%go_vendor_license_check_disable",
            defines,
            ["fedora"],
            force_license_check_enable=False,
        ).stdout
        == "0\n"
    )


def test_go_vendor_license_check_disable_default():
    assert evaluator("%go_vendor_license_check_disable").stdout == "0\n"


def test_go_vendor_license_check():
    assert (
        evaluator("%go_vendor_license_check", {"LICENSE": "MIT"}).stdout
    ) == "go_vendor_license report all --verify 'MIT'\n"


def test_go_vendor_license_check_args():
    assert (
        evaluator(
            "%go_vendor_license_check GPL-2.0-only BSD-3-Clause", {"LICENSE": "MIT"}
        ).stdout
    ) == "go_vendor_license report all --verify 'GPL-2.0-only BSD-3-Clause'\n"


def test_go_vendor_license_buildrequires():
    assert (
        evaluator("%go_vendor_license_buildrequires").stdout
        == "go_vendor_license generate_buildrequires\n"
    )


def test_go_vendor_license_buildrequires_disabled():
    assert (
        evaluator(
            "%go_vendor_license_buildrequires",
            {"go_vendor_license_check_disable": "1"},
        ).stdout
        == "go_vendor_license generate_buildrequires --no-check\n"
    )
