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

PARENT = Path(__file__).resolve().parent.parent.parent
# e.g. MACRO_DIR=%{buildroot}%{_rpmmacrodir} \
#      pytest
# MACRO_DIR="" MACRO_LUA_DIR="" to only use system paths
MACRO_DIR = str(os.environ.get("MACRO_DIR", PARENT / "rpm"))


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
    ) -> Result:
        cmd: list[str] = ["rpm", *self.macros_path]
        defines = defines or {}
        for name, value in defines.items():
            cmd.extend(("--define", f"{name} {value}"))
        for name in undefines:
            cmd.extend(("-E", f"%undefine {name}"))
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


def test_go_vendor_license_check_disabled():
    assert not (
        evaluator(
            "%go_vendor_license_check", {"go_vendor_license_check_disable": "1"}
        ).stdout.removesuffix("\n")
    )


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
