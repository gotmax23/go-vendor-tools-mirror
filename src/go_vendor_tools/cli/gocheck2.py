#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# Copyright (C) 2025 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Rewritten gocheck2 that avoids failing fast and works with GOMODULESMODE enabled.
This is meant to be run using the %gocheck2 macro and not directly.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import shlex
import subprocess
import sys
from functools import partial
from pathlib import Path

try:
    import argcomplete
except ImportError:
    HAS_ARGCOMPLETE = False
else:
    HAS_ARGCOMPLETE = True

eprint = partial(print, file=sys.stderr)


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, prog="%gocheck2")
    parser.add_argument(
        "-i",
        "--goipath",
        help="Go import path. Reads from go.mod by default.",
    )
    parser.add_argument("-I", "--ignore", nargs="*", help="Ignore individual tests")
    parser.add_argument(
        "-d",
        "--directory",
        nargs="*",
        help="Exclude the files contained in DIRECTORY non-recursively."
        " This accepts either an import path or a subdirectory of %%goipath.",
    )
    parser.add_argument(
        "-t",
        "--tree",
        nargs="*",
        help="Exclude the files contained in DIRECTORY recursively."
        " This accepts either an import path or a subdirectory of %%goipath.",
    )
    parser.add_argument(
        "-L",
        "--list",
        help="List import paths to test, but don't run anything.",
        action="store_true",
    )
    parser.add_argument("extra_args", nargs="*")
    return parser


@dataclasses.dataclass
class Args:
    goipath: str
    ignore_dirs: list[str]
    ignore_trees: list[str]
    list_only: bool
    ignored_tests: list[str]
    extra_args: list[str]


def get_goipath() -> str | None:
    gomod = Path("go.mod")
    if not gomod.is_file():
        eprint("go.mod does not exist!")
        return None
    cmd = ["go", "mod", "edit", "-json"]
    eprint(f"$ {shlex.join(cmd)}")
    proc = subprocess.run(
        ["go", "mod", "edit", "-json"], stdout=subprocess.PIPE, text=True, check=False
    )
    data = json.loads(proc.stdout) if proc.returncode == 0 else {}
    try:
        goipath = data["Module"]["Path"]
    except KeyError:
        eprint("Failed to retrieve Go import path from go.mod")
        return None
    return goipath


def parseargs() -> Args:
    ns = get_parser().parse_args()
    if not ns.goipath:
        goipath = get_goipath()
        if goipath is None:
            sys.exit(
                "Failed to determine the Go import path.\n"
                "Set %goipath in the specfile"
                " or make sure this project has a go.mod file."
            )
        ns.goipath = goipath
    return Args(
        goipath=ns.goipath,
        ignore_dirs=ns.directory or [],
        ignore_trees=ns.tree or [],
        list_only=ns.list,
        extra_args=ns.extra_args or [],
        ignored_tests=ns.ignore or [],
    )


def list_test_packages(args: Args):
    # go list command is based on one in kubernetes Makefile
    # The command is trivial and thus considered not copyrightable.
    cmd = [
        "go",
        "list",
        "-find",
        "-f",
        "{{if or (gt (len .TestGoFiles) 0) (gt (len .XTestGoFiles) 0)}}{{.ImportPath}}{{end}}",  # noqa: E501,
        f"{args.goipath}/...",
    ]
    eprint(f"$ {shlex.join(cmd)}")
    proc = subprocess.run(
        cmd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return proc.stdout.splitlines()


def main() -> None:
    args = parseargs()
    test_packages = list_test_packages(args)
    if not test_packages:
        eprint(f"No test packages found for {args.goipath}")
        return
    if args.list_only:
        print("\n".join(test_packages))
        return
    ignore_args: list[str] = []
    for ignore in args.ignored_tests:
        ignore_args.extend(("-ignore", ignore))
    cmd = ["go", "test", *ignore_args, *args.extra_args, *test_packages]
    eprint(f"$ {shlex.join(cmd)}")
    sys.exit(subprocess.run(cmd, check=False).returncode)


if __name__ == "__main__":
    main()
